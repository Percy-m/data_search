from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.database import get_db
from core.meta_models import SavedQuery

router = APIRouter()

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
def create_saved_query(query: SavedQueryCreate, db: Session = Depends(get_db)):
    # 检查是否同名
    db_query = db.query(SavedQuery).filter(SavedQuery.name == query.name).first()
    if db_query:
        raise HTTPException(status_code=400, detail="A saved query with this name already exists")
    
    new_query = SavedQuery(
        name=query.name, 
        raw_sql=query.raw_sql, 
        data_source_id=query.data_source_id,
        chart_type=query.chart_type,
        macros=query.macros,
        thresholds=query.thresholds
    )
    db.add(new_query)
    db.commit()
    db.refresh(new_query)
    return new_query

@router.get("/", response_model=List[SavedQueryResponse])
def get_saved_queries(db: Session = Depends(get_db)):
    return db.query(SavedQuery).order_by(SavedQuery.created_at.desc()).all()

@router.put("/{query_id}", response_model=SavedQueryResponse)
def update_saved_query(query_id: int, query: SavedQueryUpdate, db: Session = Depends(get_db)):
    db_query = db.query(SavedQuery).filter(SavedQuery.id == query_id).first()
    if not db_query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    if query.name is not None:
        db_query.name = query.name
    if query.raw_sql is not None:
        db_query.raw_sql = query.raw_sql
    if query.data_source_id is not None:
        db_query.data_source_id = query.data_source_id
    if query.chart_type is not None:
        db_query.chart_type = query.chart_type
    if query.macros is not None:
        db_query.macros = query.macros
    if query.thresholds is not None:
        db_query.thresholds = query.thresholds
        
    db.commit()
    db.refresh(db_query)
    return db_query

@router.delete("/{query_id}")
def delete_saved_query(query_id: int, db: Session = Depends(get_db)):
    db_query = db.query(SavedQuery).filter(SavedQuery.id == query_id).first()
    if not db_query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    db.delete(db_query)
    db.commit()
    return {"detail": "Query deleted successfully"}
