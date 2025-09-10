from pydantic import BaseModel, Field
from app.models.attendance import CheckTypeEnum

class FaceIDAttendanceCreate(BaseModel):
    """Face ID orqali davomat yaratish uchun schema"""
    employee_id: int = Field(..., description="Tanilgan xodim ID si")
    check_type: CheckTypeEnum = Field(..., description="Check in yoki check out")

class FaceIDRecognitionResult(BaseModel):
    """Face ID tanish natijasi"""
    success: bool
    message: str
    employee_id: int = None
    employee_name: str = None
    confidence: str = None
    recognized: bool = False
