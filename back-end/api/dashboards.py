from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.database import get_db
from core.meta_models import Dashboard, DashboardWidget, SavedQuery

router = APIRouter()

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

# --- Routes ---

@router.post("/", response_model=DashboardResponse)
def create_dashboard(dashboard: DashboardCreate, db: Session = Depends(get_db)):
    db_dash = db.query(Dashboard).filter(Dashboard.name == dashboard.name).first()
    if db_dash:
        raise HTTPException(status_code=400, detail="Dashboard name already exists")
    
    new_dash = Dashboard(name=dashboard.name, description=dashboard.description)
    db.add(new_dash)
    db.commit()
    db.refresh(new_dash)
    
    # Add widgets
    for w in dashboard.widgets:
        db_widget = DashboardWidget(
            dashboard_id=new_dash.id,
            query_id=w.query_id,
            x=w.x, y=w.y, w=w.w, h=w.h, i=w.i
        )
        db.add(db_widget)
    db.commit()
    db.refresh(new_dash)
    return _format_dashboard_response(new_dash)

@router.get("/", response_model=List[DashboardResponse])
def get_dashboards(db: Session = Depends(get_db)):
    dashboards = db.query(Dashboard).order_by(Dashboard.created_at.desc()).all()
    return [_format_dashboard_response(d) for d in dashboards]

@router.get("/{dash_id}", response_model=DashboardResponse)
def get_dashboard(dash_id: int, db: Session = Depends(get_db)):
    dash = db.query(Dashboard).filter(Dashboard.id == dash_id).first()
    if not dash:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return _format_dashboard_response(dash)

@router.put("/{dash_id}", response_model=DashboardResponse)
def update_dashboard(dash_id: int, dashboard: DashboardUpdate, db: Session = Depends(get_db)):
    db_dash = db.query(Dashboard).filter(Dashboard.id == dash_id).first()
    if not db_dash:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    if dashboard.name is not None:
        db_dash.name = dashboard.name
    if dashboard.description is not None:
        db_dash.description = dashboard.description
        
    # Full replace of widgets for simplicity if provided
    if dashboard.widgets is not None:
        # Delete existing
        db.query(DashboardWidget).filter(DashboardWidget.dashboard_id == dash_id).delete()
        # Insert new
        for w in dashboard.widgets:
            db_widget = DashboardWidget(
                dashboard_id=dash_id,
                query_id=w.query_id,
                x=w.x, y=w.y, w=w.w, h=w.h, i=w.i
            )
            db.add(db_widget)
            
    db.commit()
    db.refresh(db_dash)
    return _format_dashboard_response(db_dash)

@router.delete("/{dash_id}")
def delete_dashboard(dash_id: int, db: Session = Depends(get_db)):
    db_dash = db.query(Dashboard).filter(Dashboard.id == dash_id).first()
    if not db_dash:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    db.delete(db_dash)
    db.commit()
    return {"detail": "Dashboard deleted successfully"}


def _format_dashboard_response(dash: Dashboard) -> dict:
    # Helper to inject query details into the widget response
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
