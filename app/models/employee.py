from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, Numeric, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.core.database import Base

class PositionEnum(enum.Enum):
    MANAGER = "MANAGER"
    DEVELOPER = "DEVELOPER"
    DESIGNER = "DESIGNER"
    HR = "HR"
    ACCOUNTANT = "ACCOUNTANT"
    SALES = "SALES"
    MARKETING = "MARKETING"
    SUPPORT = "SUPPORT"
    INTERN = "INTERN"
    OTHER = "OTHER"

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    full_name = Column(String, nullable=False)
    position = Column(Enum(PositionEnum), nullable=True)
    phone = Column(String, nullable=True)
    photo = Column(String, nullable=True)  # Photo URL yoki base64
    base_salary = Column(Numeric(12, 2), nullable=True)  # Asosiy oylik maosh
    telegram_id = Column(BigInteger, nullable=True, unique=True)  # Telegram user ID
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False)  # Убрали timezone=True и server_default
    
    # Relationship
    attendance_records = relationship("Attendance", back_populates="employee")
