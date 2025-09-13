from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from sqladmin import Admin, ModelView
from app.core.database import Base, engine
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.routers import employees, attendance as attendance_router, mobile, statistics, face_id

app = FastAPI(
    title="📊 Workly - Ishchilar Boshqaruv Tizimi",
    description="Ishchilar davomat va ma'lum qilish tizimi",
    version="2.0.0"
)

# SQLAdmin sozlash
admin = Admin(app, engine)

# Admin uchun modellarni qo'shish
class EmployeeAdmin(ModelView, model=Employee):
    column_list = [Employee.id, Employee.full_name, Employee.position, Employee.phone, Employee.base_salary, Employee.is_active]
    column_searchable_list = [Employee.full_name, Employee.phone]
    column_sortable_list = [Employee.id, Employee.full_name, Employee.phone, Employee.base_salary]
    column_details_list = [Employee.id, Employee.full_name, Employee.position, Employee.phone, Employee.base_salary, Employee.is_active, Employee.created_at]
    column_default_sort = [(Employee.created_at, True)]  # Yaratilgan vaqt bo'yicha kamayish tartibida
    column_labels = {
        Employee.id: "ID",
        Employee.full_name: "To'liq ismi",
        Employee.position: "Lavozimi",
        Employee.phone: "Telefon",
        Employee.base_salary: "Oylik maosh",
        Employee.is_active: "Faol",
        Employee.created_at: "Yaratilgan vaqt"
    }
    name = "Xodim"
    name_plural = "Xodimlar"
    icon = "fa-solid fa-user"

class AttendanceAdmin(ModelView, model=Attendance):
    column_list = [Attendance.id, Attendance.employee_id, Attendance.check_type, Attendance.check_time, Attendance.is_late]
    column_sortable_list = [Attendance.id, Attendance.employee_id, Attendance.check_time]
    column_details_list = [Attendance.id, Attendance.employee_id, Attendance.check_type, Attendance.check_time, Attendance.is_late]
    column_default_sort = [(Attendance.check_time, True)]  # Vaqt bo'yicha kamayish tartibida (eng oxirgi birinchi)
    column_labels = {
        Attendance.id: "ID",
        Attendance.employee_id: "Xodim ID",
        Attendance.check_type: "Tur",
        Attendance.check_time: "Vaqt",
        Attendance.is_late: "Kech qolgan"
    }
    name = "Davomat"
    name_plural = "Davomat yozuvlari"
    icon = "fa-solid fa-clock"

admin.add_view(EmployeeAdmin)
admin.add_view(AttendanceAdmin)

# Upload katalogini yaratish
upload_dir = "uploads"
os.makedirs(upload_dir, exist_ok=True)

# Static files uchun
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS middleware qo'shish (mobil ilova uchun)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production da aniq domainlar ko'rsating
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event -> DB yaratish
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Routers
app.include_router(employees.router)
app.include_router(attendance_router.router)
app.include_router(mobile.router)
app.include_router(statistics.router)
app.include_router(face_id.router)

@app.get("/")
async def root():
    return {
        "message": "Workly Backend API", 
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "workly-backend"}
