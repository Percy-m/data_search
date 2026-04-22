from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List

from core.database import get_db
from core.meta_models import SavedQuery

router = APIRouter()

# Schema definitions for validation and serialization
class SavedQueryCreate(BaseModel):
    name: str
    raw_sql: str

class SavedQueryResponse(BaseModel):
    id: int
    name: str
    raw_sql: str
    created_at: datetime

    class Config:
        from_attributes = True

@router.post("/", response_model=SavedQueryResponse)
def create_saved_query(query: SavedQueryCreate, db: Session = Depends(get_db)):
    # 检查是否同名
    db_query = db.query(SavedQuery).filter(SavedQuery.name == query.name).first()
    if db_query:
        raise HTTPException(status_code=400, detail="A saved query with this name already exists")
    
    new_query = SavedQuery(name=query.name, raw_sql=query.raw_sql)
    db.add(new_query)
    db.commit()
    db.refresh(new_query)
    return new_query

@router.get("/", response_model=List[SavedQueryResponse])
def get_saved_queries(db: Session = Depends(get_db)):
    return db.query(SavedQuery).order_by(SavedQuery.created_at.desc()).all()

@router.delete("/{query_id}")
def delete_saved_query(query_id: int, db: Session = Depends(get_db)):
    db_query = db.query(SavedQuery).filter(SavedQuery.id == query_id).first()
    if not db_query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    db.delete(db_query)
    db.commit()
    return {"detail": "Query deleted successfully"}
