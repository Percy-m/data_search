from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any, Optional

from infrastructure.database import get_db
from infrastructure.repositories import SQLAlchemySavedQueryRepository
from core.ports import SavedQueryRepositoryPort

router = APIRouter()

def get_query_repository(db: Session = Depends(get_db)) -> SavedQueryRepositoryPort:
    return SQLAlchemySavedQueryRepository(db)

# Schema definitions for validation and serialization
class SavedQueryCreate(BaseModel):
    name: str
    raw_sql: str
    data_source_id: Optional[int] = None
    chart_type: str = "table"
    macros: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    thresholds: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

class SavedQueryUpdate(BaseModel):
    name: Optional[str] = None
    raw_sql: Optional[str] = None
    data_source_id: Optional[int] = None
    chart_type: Optional[str] = None
    macros: Optional[List[Dict[str, Any]]] = None
    thresholds: Optional[List[Dict[str, Any]]] = None

class SavedQueryResponse(BaseModel):
    id: int
    name: str
    raw_sql: str
    data_source_id: Optional[int]
    chart_type: str
    macros: List[Dict[str, Any]]
    thresholds: List[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

@router.post("/", response_model=SavedQueryResponse)
def create_saved_query(query: SavedQueryCreate, repo: SavedQueryRepositoryPort = Depends(get_query_repository)):
    if repo.get_by_name(query.name):
        raise HTTPException(status_code=400, detail="A saved query with this name already exists")
    
    return repo.create(query.dict())

@router.get("/", response_model=List[SavedQueryResponse])
def get_saved_queries(repo: SavedQueryRepositoryPort = Depends(get_query_repository)):
    return repo.get_all()

@router.put("/{query_id}", response_model=SavedQueryResponse)
def update_saved_query(query_id: int, query: SavedQueryUpdate, repo: SavedQueryRepositoryPort = Depends(get_query_repository)):
    existing = repo.get_by_id(query_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Query not found")
        
    if query.name is not None and query.name != existing.name:
        if repo.get_by_name(query.name):
            raise HTTPException(status_code=400, detail="A saved query with this name already exists")
            
    updated = repo.update(query_id, query.dict(exclude_unset=True))
    return updated

@router.delete("/{query_id}")
def delete_saved_query(query_id: int, repo: SavedQueryRepositoryPort = Depends(get_query_repository)):
    if not repo.delete(query_id):
        raise HTTPException(status_code=404, detail="Query not found")
    return {"detail": "Query deleted successfully"}
