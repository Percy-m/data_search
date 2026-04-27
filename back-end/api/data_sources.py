from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from infrastructure.database import get_db
from infrastructure.repositories import SQLAlchemyDataSourceRepository
from core.factory import DataSourceFactory
from core.ports import DataSourceRepositoryPort

router = APIRouter()

def get_ds_repository(db: Session = Depends(get_db)) -> DataSourceRepositoryPort:
    return SQLAlchemyDataSourceRepository(db)

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

    class Config:
        from_attributes = True

@router.post("/", response_model=DataSourceResponse)
def create_data_source(ds: DataSourceCreate, repo: DataSourceRepositoryPort = Depends(get_ds_repository)):
    if repo.get_by_name(ds.name):
        raise HTTPException(status_code=400, detail="Data source name already exists")
    
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

    return repo.create(ds.dict())

@router.get("/", response_model=List[DataSourceResponse])
def get_data_sources(repo: DataSourceRepositoryPort = Depends(get_ds_repository)):
    return repo.get_all()

@router.put("/{ds_id}", response_model=DataSourceResponse)
def update_data_source(ds_id: int, ds: DataSourceUpdate, repo: DataSourceRepositoryPort = Depends(get_ds_repository)):
    db_ds = repo.get_by_id(ds_id)
    if not db_ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    if ds.name is not None and ds.name != db_ds.name:
        if repo.get_by_name(ds.name):
            raise HTTPException(status_code=400, detail="Data source name already exists")
    
    test_type = ds.type if ds.type is not None else db_ds.type
    test_host = ds.host if ds.host is not None else db_ds.host
    test_port = ds.port if ds.port is not None else db_ds.port
    test_username = ds.username if ds.username is not None else db_ds.username
    test_password = ds.password if ds.password else db_ds.password
    test_database = ds.database if ds.database is not None else db_ds.database

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

    update_data = {k: v for k, v in ds.dict(exclude_unset=True).items()}
    if 'password' in update_data and not update_data['password']:
        del update_data['password']

    updated_ds = repo.update(ds_id, update_data)
    return updated_ds

@router.delete("/{ds_id}")
def delete_data_source(ds_id: int, repo: DataSourceRepositoryPort = Depends(get_ds_repository)):
    if not repo.delete(ds_id):
        raise HTTPException(status_code=404, detail="Data source not found")
    return {"detail": "Data source deleted"}
