"""SQLAlchemy ORM models"""

import uuid
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, Float, Index
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


def new_id() -> str:
    return str(uuid.uuid4())


class Job(Base):
    __tablename__ = "jobs"

    id            = Column(String, primary_key=True, default=new_id)
    title         = Column(String(300), nullable=False)
    company       = Column(String(200), nullable=False, default="Unknown")
    location      = Column(String(200), default="South Africa")
    province      = Column(String(100))
    is_remote     = Column(Boolean, default=False)
    category      = Column(String(100))
    job_type      = Column(String(50), default="full-time")
    salary_min    = Column(Float, nullable=True)
    salary_max    = Column(Float, nullable=True)
    salary        = Column(String(150))
    description   = Column(Text)
    url           = Column(String(1000), nullable=False, unique=True)
    source        = Column(String(100))
    fingerprint   = Column(String(64), unique=True)
    is_active     = Column(Boolean, default=True)
    is_featured   = Column(Boolean, default=False)
    posted_at     = Column(String(100), nullable=True)
    fetched_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, onupdate=func.now())

    __table_args__ = (
        Index("ix_jobs_category", "category"),
        Index("ix_jobs_is_remote", "is_remote"),
        Index("ix_jobs_posted_at", "posted_at"),
        Index("ix_jobs_source", "source"),
    )


class JobAlert(Base):
    __tablename__ = "job_alerts"

    id         = Column(String, primary_key=True, default=new_id)
    email      = Column(String(300), nullable=False)
    keyword    = Column(String(200))
    location   = Column(String(200))
    category   = Column(String(100))
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_sent  = Column(DateTime, nullable=True)


class FetchLog(Base):
    __tablename__ = "fetch_logs"

    id         = Column(String, primary_key=True, default=new_id)
    source     = Column(String(100))
    status     = Column(String(50))
    jobs_found = Column(Integer, default=0)
    jobs_new   = Column(Integer, default=0)
    error_msg  = Column(Text, nullable=True)
    ran_at     = Column(DateTime, server_default=func.now())
