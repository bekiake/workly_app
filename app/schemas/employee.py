from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class EmployeeBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    position: Optional[str] = None
    phone: Optional[str] = None
    photo: Optional[str] = None
    base_salary: Optional[Decimal] = None
    telegram_id: Optional[int] = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    photo: Optional[str] = None
    base_salary: Optional[Decimal] = None
    telegram_id: Optional[int] = None
    is_active: Optional[bool] = None

class Employee(EmployeeBase):
    id: int
    uuid: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
