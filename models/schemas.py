from pydantic import BaseModel
from typing import Optional, List


class JobOut(BaseModel):
    id: int
    title: str
    company: str
    location: Optional[str] = None
    province: Optional[str] = None
    is_remote: bool = False
    category: Optional[str] = None
    job_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_text: Optional[str] = None
    description: Optional[str] = None
    url: str
    source: Optional[str] = None
    is_featured: bool = False
    posted_at: Optional[str] = None
    fetched_at: Optional[str] = None

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


class AlertOut(BaseModel):
    id: int
    email: str
    keyword: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[str] = None


class StatsOut(BaseModel):
    total_jobs: int
    remote_jobs: int
    tech_jobs: int
    sources: List[dict]
    last_updated: Optional[str] = None


class ScrapeLogOut(BaseModel):
    id: int
    source: Optional[str] = None
    jobs_found: int = 0
    jobs_new: int = 0
    status: Optional[str] = None
    error_msg: Optional[str] = None
    ran_at: Optional[str] = None
