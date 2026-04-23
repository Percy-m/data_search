from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from core.database import get_db
from core.meta_models import DataSource
from core.factory import DataSourceFactory

router = APIRouter()

class DataSourceCreate(BaseModel):
    name: str
    type: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None

class DataSourceResponse(BaseModel):
    id: int
    name: str
    type: str
    host: str
    port: int
    username: Optional[str]
    database: Optional[str]
    created_at: datetime
    # Intentionally omitted password from response

    class Config:
        from_attributes = True

@router.post("/", response_model=DataSourceResponse)
def create_data_source(ds: DataSourceCreate, db: Session = Depends(get_db)):
    db_ds = db.query(DataSource).filter(DataSource.name == ds.name).first()
    if db_ds:
        raise HTTPException(status_code=400, detail="Data source name already exists")
    
    # Try to test connection before saving
    try:
        adapter = DataSourceFactory.create(
            ds.type,
            host=ds.host,
            port=ds.port,
            username=ds.username,
            password=ds.password,
            database=ds.database
        )
        if not adapter.test_connection():
            raise HTTPException(status_code=400, detail="Connection test failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect: {str(e)}")

    new_ds = DataSource(**ds.dict())
    db.add(new_ds)
    db.commit()
    db.refresh(new_ds)
    return new_ds

@router.get("/", response_model=List[DataSourceResponse])
def get_data_sources(db: Session = Depends(get_db)):
    return db.query(DataSource).all()

@router.delete("/{ds_id}")
def delete_data_source(ds_id: int, db: Session = Depends(get_db)):
    db_ds = db.query(DataSource).filter(DataSource.id == ds_id).first()
    if not db_ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    db.delete(db_ds)
    db.commit()
    return {"detail": "Data source deleted"}
