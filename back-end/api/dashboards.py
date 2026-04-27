from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any, Optional

from infrastructure.database import get_db
from infrastructure.repositories import SQLAlchemyDashboardRepository
from core.ports import DashboardRepositoryPort

router = APIRouter()

def get_dash_repository(db: Session = Depends(get_db)) -> DashboardRepositoryPort:
    return SQLAlchemyDashboardRepository(db)

# --- Schemas ---
class WidgetCreate(BaseModel):
    query_id: int
    x: int = 0
    y: int = 0
    w: int = 12
    h: int = 8
    i: str

class WidgetResponse(WidgetCreate):
    id: int
    # We will embed the query details directly for the frontend to render
    query_name: Optional[str] = None
    query_sql: Optional[str] = None
    query_thresholds: Optional[List[Dict[str, Any]]] = None
    chart_type: str = "table"
    data_source_id: Optional[int] = None

    class Config:
        from_attributes = True

class DashboardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    widgets: List[WidgetCreate] = []

class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    widgets: Optional[List[WidgetCreate]] = None

class DashboardResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    widgets: List[WidgetResponse] = []

    class Config:
        from_attributes = True

def _format_dashboard_response(dash: Any) -> dict:
    resp = {
        "id": dash.id,
        "name": dash.name,
        "description": dash.description,
        "created_at": dash.created_at,
        "widgets": []
    }
    for w in dash.widgets:
        q = w.query
        resp["widgets"].append({
            "id": w.id,
            "query_id": w.query_id,
            "x": w.x, "y": w.y, "w": w.w, "h": w.h, "i": w.i,
            "query_name": q.name if q else "Unknown",
            "query_sql": q.raw_sql if q else "",
            "query_thresholds": q.thresholds if q else [],
            "chart_type": q.chart_type if q else "table",
            "data_source_id": q.data_source_id if q else None
        })
    return resp

# --- Routes ---

@router.post("/", response_model=DashboardResponse)
def create_dashboard(dashboard: DashboardCreate, repo: DashboardRepositoryPort = Depends(get_dash_repository)):
    if repo.get_by_name(dashboard.name):
        raise HTTPException(status_code=400, detail="Dashboard name already exists")
    
    new_dash = repo.create(dashboard.dict())
    return _format_dashboard_response(new_dash)

@router.get("/", response_model=List[DashboardResponse])
def get_dashboards(repo: DashboardRepositoryPort = Depends(get_dash_repository)):
    dashboards = repo.get_all()
    return [_format_dashboard_response(d) for d in dashboards]

@router.get("/{dash_id}", response_model=DashboardResponse)
def get_dashboard(dash_id: int, repo: DashboardRepositoryPort = Depends(get_dash_repository)):
    dash = repo.get_by_id(dash_id)
    if not dash:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return _format_dashboard_response(dash)

@router.put("/{dash_id}", response_model=DashboardResponse)
def update_dashboard(dash_id: int, dashboard: DashboardUpdate, repo: DashboardRepositoryPort = Depends(get_dash_repository)):
    existing = repo.get_by_id(dash_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    if dashboard.name is not None and dashboard.name != existing.name:
        if repo.get_by_name(dashboard.name):
            raise HTTPException(status_code=400, detail="Dashboard name already exists")
            
    updated = repo.update(dash_id, dashboard.dict(exclude_unset=True))
    return _format_dashboard_response(updated)

@router.delete("/{dash_id}")
def delete_dashboard(dash_id: int, repo: DashboardRepositoryPort = Depends(get_dash_repository)):
    if not repo.delete(dash_id):
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return {"detail": "Dashboard deleted successfully"}