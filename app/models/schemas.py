from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class JobOut(BaseModel):
    id: str
    title: str
    company: str
    location: str
    salary: Optional[str] = None
    description: Optional[str] = None
    url: str
    source: Optional[str] = None
    category: Optional[str] = None
    job_type: Optional[str] = None
    is_remote: bool = False
    is_featured: bool = False
    posted_at: Optional[str] = None
    fetched_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobsResponse(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    jobs: List[JobOut]


class AlertCreate(BaseModel):
    email: str
    keyword: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None


class AlertOut(BaseModel):
    id: str
    email: str
    keyword: Optional[str]
    location: Optional[str]
    category: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class FetchLogOut(BaseModel):
    id: str
    source: Optional[str]
    status: Optional[str]
    jobs_found: int
    jobs_new: int
    error_msg: Optional[str]
    ran_at: Optional[datetime]

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    total_jobs: int
    remote_jobs: int
    tech_jobs: int
    sources: List[dict]
    last_updated: Optional[str]
