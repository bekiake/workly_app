from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional
from app.models.attendance import CheckTypeEnum, SourceEnum

class AttendanceBase(BaseModel):
    check_type: CheckTypeEnum
    source: Optional[SourceEnum] = SourceEnum.APP

class AttendanceCreate(AttendanceBase):
    employee_uuid: str = Field(..., description="Employee UUID from QR code")
    location_lat: Optional[str] = None
    location_lon: Optional[str] = None

class AttendanceUpdate(BaseModel):
    check_type: Optional[CheckTypeEnum] = None
    source: Optional[SourceEnum] = None

class Attendance(AttendanceBase):
    id: int
    employee_id: int
    check_time: datetime
    location_lat: Optional[str] = None
    location_lon: Optional[str] = None
    is_late: bool = False
    is_early_departure: bool = False

    class Config:
        from_attributes = True

class AttendanceWithEmployee(Attendance):
    employee_name: str
    employee_position: str

class QRScanRequest(BaseModel):
    qr_code: str = Field(..., description="QR code content (employee UUID)")
    check_type: CheckTypeEnum = Field(..., description="Check in or check out")

class AttendanceReport(BaseModel):
    employee_id: int
    employee_name: str
    position: str
    total_days: int
    present_days: int
    late_days: int
    early_departure_days: int
    total_hours: float
    month: int
    year: int

class DailyWorkStats(BaseModel):
    """Kunlik ish statistikasi"""
    date: date
    worked_hours: float
    status: str  # absent, incomplete, complete, full_day, half_day, short_day, not_checked_out
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    is_late: bool = False
    is_early_departure: bool = False
    late_minutes: int = 0
    early_departure_minutes: int = 0

class SalaryDeduction(BaseModel):
    """Maosh uderzhaniya ma'lumotlari"""
    days: Optional[int] = None
    hours: Optional[float] = None
    amount: float

class SalaryInfo(BaseModel):
    """Maosh hisob-kitobi"""
    base_salary: float
    daily_salary: float
    hourly_salary: float
    total_deductions: float
    final_salary: float
    worked_hours: float
    expected_hours: float
    deduction_breakdown: dict[str, SalaryDeduction]

class MonthlyEmployeeStats(BaseModel):
    """Xodimning oylik statistikasi"""
    employee_id: int
    employee_name: str
    position: str
    month: int
    year: int
    working_days: int
    present_days: int
    absent_days: int
    late_days: int
    early_departure_days: int
    total_worked_hours: float
    expected_hours: float
    total_late_minutes: int
    total_early_departure_minutes: int
    attendance_rate: float
    punctuality_rate: float
    salary_info: SalaryInfo
    daily_stats: list[DailyWorkStats]

class WorkTimeConfig(BaseModel):
    """Ish vaqti sozlamalari"""
    work_start: str
    work_end: str
    lunch_start: str
    lunch_end: str
    working_hours_per_day: float
    check_in_window: str
    check_out_window: str
