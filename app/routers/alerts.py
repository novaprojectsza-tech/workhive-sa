from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import JobAlert
from app.models.database import get_db
from app.models.schemas import AlertCreate, AlertOut

router = APIRouter()


@router.post("", response_model=AlertOut, status_code=201)
async def create_alert(payload: AlertCreate, db: AsyncSession = Depends(get_db)):
    alert = JobAlert(**payload.model_dump())
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    alert = await db.get(JobAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_active = False
    await db.commit()
    return {"status": "unsubscribed"}
