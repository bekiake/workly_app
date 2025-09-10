from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

class CheckTypeEnum(enum.Enum):
    IN = "IN"
    OUT = "OUT"

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"))
    check_type = Column(Enum(CheckTypeEnum), nullable=False)
    check_time = Column(DateTime(timezone=True), server_default=func.now())
    is_late = Column(Boolean, default=False)  # Kechikish (faqat IN uchun)
    is_early_departure = Column(Boolean, default=False)  # Erta ketish (faqat OUT uchun)
    
    # Relationship
    employee = relationship("Employee", back_populates="attendance_records")
