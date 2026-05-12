from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.ports import ComparisonConfigRepositoryPort
from infrastructure.database import get_db
from infrastructure.repositories import SQLAlchemyComparisonConfigRepository

router = APIRouter()


def get_comparison_repository(db: Session = Depends(get_db)) -> ComparisonConfigRepositoryPort:
    return SQLAlchemyComparisonConfigRepository(db)


class ComparisonConfigCreate(BaseModel):
    name: str
    data_source_id: Optional[int] = None
    raw_sql: str
    baseline_name: str = "baseline"
    target_name: str = "target"
    baseline_macros: Dict[str, str] = Field(default_factory=dict)
    target_macros: Dict[str, str] = Field(default_factory=dict)
    key_columns: List[str] = Field(default_factory=list)
    group_columns: List[str] = Field(default_factory=list)
    criteria: List[Dict[str, Any]] = Field(default_factory=list)
    compare_columns: List[str] = Field(default_factory=list)
    max_rows: int = 100000


class ComparisonConfigUpdate(BaseModel):
    name: Optional[str] = None
    data_source_id: Optional[int] = None
    raw_sql: Optional[str] = None
    baseline_name: Optional[str] = None
    target_name: Optional[str] = None
    baseline_macros: Optional[Dict[str, str]] = None
    target_macros: Optional[Dict[str, str]] = None
    key_columns: Optional[List[str]] = None
    group_columns: Optional[List[str]] = None
    criteria: Optional[List[Dict[str, Any]]] = None
    compare_columns: Optional[List[str]] = None
    max_rows: Optional[int] = None


class ComparisonConfigResponse(BaseModel):
    id: int
    name: str
    data_source_id: Optional[int]
    raw_sql: str
    baseline_name: str
    target_name: str
    baseline_macros: Dict[str, str]
    target_macros: Dict[str, str]
    key_columns: List[str]
    group_columns: List[str]
    criteria: List[Dict[str, Any]]
    compare_columns: List[str]
    max_rows: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=ComparisonConfigResponse)
def create_comparison_config(config: ComparisonConfigCreate, repo: ComparisonConfigRepositoryPort = Depends(get_comparison_repository)):
    if repo.get_by_name(config.name):
        raise HTTPException(status_code=400, detail="A comparison config with this name already exists")
    return repo.create(config.dict())


@router.get("/", response_model=List[ComparisonConfigResponse])
def get_comparison_configs(repo: ComparisonConfigRepositoryPort = Depends(get_comparison_repository)):
    return repo.get_all()


@router.get("/{comparison_id}", response_model=ComparisonConfigResponse)
def get_comparison_config(comparison_id: int, repo: ComparisonConfigRepositoryPort = Depends(get_comparison_repository)):
    config = repo.get_by_id(comparison_id)
    if not config:
        raise HTTPException(status_code=404, detail="Comparison config not found")
    return config


@router.put("/{comparison_id}", response_model=ComparisonConfigResponse)
def update_comparison_config(comparison_id: int, config: ComparisonConfigUpdate, repo: ComparisonConfigRepositoryPort = Depends(get_comparison_repository)):
    existing = repo.get_by_id(comparison_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Comparison config not found")

    if config.name is not None and config.name != existing.name:
        if repo.get_by_name(config.name):
            raise HTTPException(status_code=400, detail="A comparison config with this name already exists")

    return repo.update(comparison_id, config.dict(exclude_unset=True))


@router.delete("/{comparison_id}")
def delete_comparison_config(comparison_id: int, repo: ComparisonConfigRepositoryPort = Depends(get_comparison_repository)):
    if not repo.delete(comparison_id):
        raise HTTPException(status_code=404, detail="Comparison config not found")
    return {"detail": "Comparison config deleted successfully"}
