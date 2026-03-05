"""Auth + Applications routes"""

import os, uuid
from fastapi import APIRouter, Response, Request, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, Column, String, DateTime, Boolean
from sqlalchemy.sql import func
from passlib.context import CryptContext
import jwt as pyjwt
from datetime import datetime, timedelta
from app.models.database import get_db
from app.models.models import Base, Job

router = APIRouter()

def new_id(): return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id            = Column(String, primary_key=True, default=new_id)
    name          = Column(String(200), nullable=False)
    email         = Column(String(300), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role          = Column(String(50), default="user")
    created_at    = Column(DateTime, server_default=func.now())

class Application(Base):
    __tablename__ = "applications"
    id         = Column(String, primary_key=True, default=new_id)
    user_id    = Column(String, nullable=False)
    job_id     = Column(String, nullable=False)
    job_title  = Column(String(300))
    company    = Column(String(200))
    status     = Column(String(50), default="applied")
    notes      = Column(String(1000))
    applied_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET", "workhive-sa-change-before-deploy")

def make_token(u):
    exp = datetime.utcnow() + timedelta(days=7)
    return pyjwt.encode({"id":u.id,"name":u.name,"email":u.email,"role":u.role,"exp":exp}, JWT_SECRET, algorithm="HS256")

def get_current_user(request: Request):
    token = request.cookies.get("token") or request.headers.get("Authorization","").replace("Bearer ","")
    if not token: raise HTTPException(401, "Not authenticated")
    try: return pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except: raise HTTPException(401, "Invalid token")

class RegisterIn(BaseModel):
    name: str; email: str; password: str

class LoginIn(BaseModel):
    email: str; password: str

class AppCreate(BaseModel):
    job_id: str; notes: str = ""

class AppUpdate(BaseModel):
    status: str = None; notes: str = None

@router.post("/register")
async def register(body: RegisterIn, response: Response, db: AsyncSession = Depends(get_db)):
    if (await db.execute(select(User).where(User.email==body.email))).scalar_one_or_none():
        raise HTTPException(400,"Email already registered")
    u = User(name=body.name, email=body.email, password_hash=pwd_ctx.hash(body.password))
    db.add(u); await db.commit(); await db.refresh(u)
    response.set_cookie("token", make_token(u), httponly=True, max_age=604800, samesite="lax")
    return {"user":{"id":u.id,"name":u.name,"email":u.email,"role":u.role}}

@router.post("/login")
async def login(body: LoginIn, response: Response, db: AsyncSession = Depends(get_db)):
    u = (await db.execute(select(User).where(User.email==body.email))).scalar_one_or_none()
    if not u or not pwd_ctx.verify(body.password, u.password_hash):
        raise HTTPException(401,"Invalid credentials")
    response.set_cookie("token", make_token(u), httponly=True, max_age=604800, samesite="lax")
    return {"user":{"id":u.id,"name":u.name,"email":u.email,"role":u.role}}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("token"); return {"success":True}

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {"user":user}

# ── Applications ──────────────────────────────────────────────────────────────
app_router = APIRouter()

@app_router.get("")
async def list_apps(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.user_id==user["id"]).order_by(Application.applied_at.desc()))
    apps = result.scalars().all()
    out = []
    for a in apps:
        job = (await db.execute(select(Job).where(Job.id==a.job_id))).scalar_one_or_none()
        out.append({"id":a.id,"job_id":a.job_id,"job_title":a.job_title,"company":a.company,
                    "job_url":job.url if job else None,"status":a.status,"notes":a.notes,"applied_at":str(a.applied_at)})
    return out

@app_router.post("")
async def create_app(body: AppCreate, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(Job).where(Job.id==body.job_id))).scalar_one_or_none()
    if not job: raise HTTPException(404,"Job not found")
    if (await db.execute(select(Application).where(Application.user_id==user["id"],Application.job_id==body.job_id))).scalar_one_or_none():
        raise HTTPException(400,"Already tracking this job")
    a = Application(user_id=user["id"],job_id=body.job_id,job_title=job.title,company=job.company,notes=body.notes)
    db.add(a); await db.commit(); await db.refresh(a)
    return {"id":a.id,"success":True}

@app_router.patch("/{app_id}")
async def update_app(app_id: str, body: AppUpdate, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    a = (await db.execute(select(Application).where(Application.id==app_id,Application.user_id==user["id"]))).scalar_one_or_none()
    if not a: raise HTTPException(404,"Not found")
    if body.status: a.status = body.status
    if body.notes is not None: a.notes = body.notes
    await db.commit(); return {"success":True}

@app_router.delete("/{app_id}")
async def delete_app(app_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    a = (await db.execute(select(Application).where(Application.id==app_id,Application.user_id==user["id"]))).scalar_one_or_none()
    if not a: raise HTTPException(404,"Not found")
    await db.delete(a); await db.commit(); return {"success":True}
