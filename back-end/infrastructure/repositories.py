from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from core.ports import DataSourceRepositoryPort, SavedQueryRepositoryPort, DashboardRepositoryPort
from infrastructure.orm_models import DataSource, SavedQuery, Dashboard, DashboardWidget
from core.models import DashboardAggregateDTO, DashboardWidgetDTO

class SQLAlchemyDataSourceRepository(DataSourceRepositoryPort):
    def __init__(self, db: Session):
        self.db = db
        
    def get_by_id(self, id: int) -> Optional[DataSource]:
        return self.db.query(DataSource).filter(DataSource.id == id).first()
        
    def get_by_name(self, name: str) -> Optional[DataSource]:
        return self.db.query(DataSource).filter(DataSource.name == name).first()
        
    def get_all(self) -> List[DataSource]:
        return self.db.query(DataSource).all()
        
    def create(self, data: Dict[str, Any]) -> DataSource:
        new_ds = DataSource(**data)
        self.db.add(new_ds)
        self.db.commit()
        self.db.refresh(new_ds)
        return new_ds
        
    def update(self, id: int, data: Dict[str, Any]) -> Optional[DataSource]:
        ds = self.get_by_id(id)
        if ds:
            for key, value in data.items():
                setattr(ds, key, value)
            self.db.commit()
            self.db.refresh(ds)
        return ds
        
    def delete(self, id: int) -> bool:
        ds = self.get_by_id(id)
        if ds:
            self.db.delete(ds)
            self.db.commit()
            return True
        return False

class SQLAlchemySavedQueryRepository(SavedQueryRepositoryPort):
    def __init__(self, db: Session):
        self.db = db
        
    def get_by_id(self, id: int) -> Optional[SavedQuery]:
        return self.db.query(SavedQuery).filter(SavedQuery.id == id).first()
        
    def get_by_name(self, name: str) -> Optional[SavedQuery]:
        return self.db.query(SavedQuery).filter(SavedQuery.name == name).first()
        
    def get_all(self) -> List[SavedQuery]:
        return self.db.query(SavedQuery).order_by(SavedQuery.created_at.desc()).all()
        
    def create(self, data: Dict[str, Any]) -> SavedQuery:
        new_query = SavedQuery(**data)
        self.db.add(new_query)
        self.db.commit()
        self.db.refresh(new_query)
        return new_query
        
    def update(self, id: int, data: Dict[str, Any]) -> Optional[SavedQuery]:
        query = self.get_by_id(id)
        if query:
            for key, value in data.items():
                setattr(query, key, value)
            self.db.commit()
            self.db.refresh(query)
        return query
        
    def delete(self, id: int) -> bool:
        query = self.get_by_id(id)
        if query:
            self.db.query(DashboardWidget).filter(DashboardWidget.query_id == id).delete()
            self.db.delete(query)
            self.db.commit()
            return True
        return False

class SQLAlchemyDashboardRepository(DashboardRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    def _assemble_aggregate(self, dash: Dashboard) -> DashboardAggregateDTO:
        widgets = self.db.query(DashboardWidget).filter(DashboardWidget.dashboard_id == dash.id).all()
        
        query_ids = [w.query_id for w in widgets]
        queries_map = {}
        if query_ids:
            queries = self.db.query(SavedQuery).filter(SavedQuery.id.in_(query_ids)).all()
            queries_map = {q.id: q for q in queries}

        widget_dtos = []
        for w in widgets:
            widget_dtos.append(DashboardWidgetDTO(
                id=w.id,
                dashboard_id=w.dashboard_id,
                query_id=w.query_id,
                x=w.x, y=w.y, w=w.w, h=w.h, i=w.i,
                query=queries_map.get(w.query_id)
            ))
            
        return DashboardAggregateDTO(
            id=dash.id,
            name=dash.name,
            description=dash.description,
            created_at=dash.created_at,
            widgets=widget_dtos
        )
        
    def get_by_id(self, id: int) -> Optional[DashboardAggregateDTO]:
        dash = self.db.query(Dashboard).filter(Dashboard.id == id).first()
        if not dash: return None
        return self._assemble_aggregate(dash)
        
    def get_by_name(self, name: str) -> Optional[DashboardAggregateDTO]:
        dash = self.db.query(Dashboard).filter(Dashboard.name == name).first()
        if not dash: return None
        return self._assemble_aggregate(dash)
        
    def get_all(self) -> List[DashboardAggregateDTO]:
        dashboards = self.db.query(Dashboard).order_by(Dashboard.created_at.desc()).all()
        return [self._assemble_aggregate(d) for d in dashboards]
        
    def create(self, data: Dict[str, Any]) -> DashboardAggregateDTO:
        widgets_data = data.pop('widgets', [])
        new_dash = Dashboard(**data)
        self.db.add(new_dash)
        self.db.flush()
        
        for w in widgets_data:
            db_widget = DashboardWidget(
                dashboard_id=new_dash.id,
                query_id=w['query_id'],
                x=w.get('x', 0), y=w.get('y', 0), w=w.get('w', 12), h=w.get('h', 8), i=w['i']
            )
            self.db.add(db_widget)
        self.db.commit()
        return self.get_by_id(new_dash.id)
        
    def update(self, id: int, data: Dict[str, Any]) -> Optional[DashboardAggregateDTO]:
        dash = self.db.query(Dashboard).filter(Dashboard.id == id).first()
        if not dash: return None
        
        widgets_data = data.pop('widgets', None)
        
        for key, value in data.items():
            setattr(dash, key, value)
            
        if widgets_data is not None:
            self.db.query(DashboardWidget).filter(DashboardWidget.dashboard_id == id).delete()
            for w in widgets_data:
                db_widget = DashboardWidget(
                    dashboard_id=id,
                    query_id=w['query_id'],
                    x=w.get('x', 0), y=w.get('y', 0), w=w.get('w', 12), h=w.get('h', 8), i=w['i']
                )
                self.db.add(db_widget)
                
        self.db.commit()
        return self.get_by_id(dash.id)
        
    def delete(self, id: int) -> bool:
        dash = self.db.query(Dashboard).filter(Dashboard.id == id).first()
        if dash:
            self.db.query(DashboardWidget).filter(DashboardWidget.dashboard_id == id).delete()
            self.db.delete(dash)
            self.db.commit()
            return True
        return False




