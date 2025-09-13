from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, Boolean, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

class CheckTypeEnum(enum.Enum):
    IN = "IN"
    OUT = "OUT"

class SourceEnum(enum.Enum):
    APP = "APP"
    TELEGRAM = "TELEGRAM"

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"))
    check_type = Column(Enum(CheckTypeEnum), nullable=False)
    source = Column(Enum(SourceEnum), nullable=False, default=SourceEnum.APP)
    check_time = Column(DateTime, nullable=False)  # Убрали timezone=True
    location_lat = Column(String, nullable=True)  # Latitude для геолокации
    location_lon = Column(String, nullable=True)  # Longitude для геолокации
    is_late = Column(Boolean, default=False)  # Kechikish (faqat IN uchun)
    
    # Relationship
    employee = relationship("Employee", back_populates="attendance_records")
