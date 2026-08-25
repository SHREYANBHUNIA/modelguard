"""SQLAlchemy persistence for model configurations, runs, and report summaries."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


DATABASE_URL = os.getenv("MODEL_GUARD_DATABASE_URL", "sqlite:///./modelguard.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class TestConfiguration(Base):
    __tablename__ = "model_test_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    model_name: Mapped[str] = mapped_column(String(160), nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(32), nullable=False, default="linear_score")
    artifact_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    model_spec: Mapped[dict] = mapped_column(JSON, nullable=False)
    baseline_model_spec: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    test_definitions: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    runs: Mapped[list["TestRun"]] = relationship(back_populates="configuration", cascade="all, delete-orphan")


class TestRun(Base):
    __tablename__ = "model_test_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    configuration_id: Mapped[str] = mapped_column(ForeignKey("model_test_configurations.id"), nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(32), nullable=False)
    artifact_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    baseline_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    report: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    configuration: Mapped[TestConfiguration] = relationship(back_populates="runs")
    report_summary: Mapped["ReportSummary"] = relationship(back_populates="run", cascade="all, delete-orphan", uselist=False)


class ReportSummary(Base):
    __tablename__ = "model_test_report_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("model_test_runs.id"), nullable=False, unique=True)
    share_token: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    aggregate_status: Mapped[str] = mapped_column(String(24), nullable=False)
    totals: Mapped[dict] = mapped_column(JSON, nullable=False)
    baseline_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    run: Mapped[TestRun] = relationship(back_populates="report_summary")


def create_schema() -> None:
    Base.metadata.create_all(bind=engine)


def session_scope():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
