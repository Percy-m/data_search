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

class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
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

@router.put("/{ds_id}", response_model=DataSourceResponse)
def update_data_source(ds_id: int, ds: DataSourceUpdate, db: Session = Depends(get_db)):
    db_ds = db.query(DataSource).filter(DataSource.id == ds_id).first()
    if not db_ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    if ds.name is not None and ds.name != db_ds.name:
        existing = db.query(DataSource).filter(DataSource.name == ds.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Data source name already exists")
    
    # Collect new values for testing connection
    test_type = ds.type if ds.type is not None else db_ds.type
    test_host = ds.host if ds.host is not None else db_ds.host
    test_port = ds.port if ds.port is not None else db_ds.port
    test_username = ds.username if ds.username is not None else db_ds.username
    # For password, if not provided in update (None or empty string), use existing password for testing
    test_password = ds.password if ds.password else db_ds.password
    test_database = ds.database if ds.database is not None else db_ds.database

    # Try to test connection before saving
    try:
        adapter = DataSourceFactory.create(
            test_type,
            host=test_host,
            port=test_port,
            username=test_username,
            password=test_password,
            database=test_database
        )
        if not adapter.test_connection():
            raise HTTPException(status_code=400, detail="Connection test failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect: {str(e)}")

    # Update fields
    if ds.name is not None: db_ds.name = ds.name
    if ds.type is not None: db_ds.type = ds.type
    if ds.host is not None: db_ds.host = ds.host
    if ds.port is not None: db_ds.port = ds.port
    if ds.username is not None: db_ds.username = ds.username
    # Only update password if a non-empty string is provided
    if ds.password: db_ds.password = ds.password
    if ds.database is not None: db_ds.database = ds.database

    db.commit()
    db.refresh(db_ds)
    return db_ds

@router.delete("/{ds_id}")
def delete_data_source(ds_id: int, db: Session = Depends(get_db)):
    db_ds = db.query(DataSource).filter(DataSource.id == ds_id).first()
    if not db_ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    db.delete(db_ds)
    db.commit()
    return {"detail": "Data source deleted"}
