from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any


class ProjectBase(BaseModel):
    product_name: str
    product_description: str
    target_audience: str
    unique_selling_points: List[str]


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase):
    id: int
    user_id: int
    content: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectList(BaseModel):
    id: int
    product_name: str
    target_audience: str
    created_at: datetime

    class Config:
        from_attributes = True
