# Workly - Xodimlar Davomat Nazorati Tizimi 📱

## Loyiha haqida

Workly - bu ishxona xodimlarining kelish-ketish vaqtlarini Face ID va QR kod orqali nazorat qilish uchun mo'ljallangan zamonaviy backend API tizimi. FastAPI frameworki asosida qurilgan.

### Asosiy xususiyatlar:

- 🔐 **QR kod orqali autentifikatsiya** - Har bir xodim uchun noyob UUID asosida QR kod
- 👤 **Face ID** - Yuz tanish texnologiyasi orqali davomat nazorati  
- ⏰ **Vaqt nazorati** - Kelish/ketish vaqtlarini aniq yozib olish
- 📊 **Hisobotlar** - Oylik Excel hisobotlari va statistika
- 📱 **Mobil API** - Planshet va mobil ilovalar uchun optimallashtirilgan
- 🕘 **Kechikish nazorati** - 9:00 dan keyin kelganlarni avtomatik aniqlash
- 💰 **Maosh hisoblash** - Asosiy oylik maosh va bonuslar nazorati

## O'rnatish

### 1. Loyihani klonlash
```bash
git clone <repo-url>
cd workly_app
```

### 2. Virtual muhit yaratish
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# yoki
source venv/bin/activate  # Linux/Mac
```

### 3. Paketlarni o'rnatish
```bash
pip install -r requirements.txt
```

### 4. Ma'lumotlar bazasini sozlash va sample ma'lumotlar yaratish
```bash
# Ma'lumotlar bazasi jadvallarini yaratish va sample ma'lumotlarni yuklash
python create_sample_data.py
```

Bu skript quyidagilarni bajaradi:
- Database jadvallarini avtomatik yaratadi
- 10 ta sample xodim ma'lumotlarini qo'shadi
- Oxirgi 30 kun uchun tasodifiy davomat yozuvlarini yaratadi

## Ishga tushirish

```bash
# Development rejimida
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production rejimida
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API dokumentatsiya: http://localhost:8000/docs  
Alternative dokumentatsiya: http://localhost:8000/redoc

## API Endpoints

### Xodimlar (Employees)
- `POST /employees/` - Yangi xodim yaratish
- `GET /employees/` - Barcha xodimlar ro'yxati
- `GET /employees/{id}` - ID bo'yicha xodim
- `GET /employees/uuid/{uuid}` - UUID bo'yicha xodim
- `PUT /employees/{id}` - Xodim ma'lumotlarini yangilash
- `DELETE /employees/{id}` - Xodimni o'chirish (soft delete)

### Xodim rasmlari
- `POST /employees/{id}/photo` - Rasm yuklash
- `GET /employees/{id}/photo` - Rasmni olish  
- `DELETE /employees/{id}/photo` - Rasmni o'chirish

### Statistika va hisobotlar
- `GET /statistics/summary` - Umumiy statistika
- `GET /statistics/daily/{date}` - Kunlik statistika  
- `GET /statistics/monthly/{year}/{month}` - Oylik statistika
- `GET /statistics/employee/{employee_id}` - Xodim statistikasi

### Mobile API
- `POST /mobile/scan` - QR kod skanerlash
- `GET /mobile/employee/{uuid}` - UUID bo'yicha xodim
- `GET /mobile/today-attendance/{employee_id}` - Bugungi davomat
- `POST /mobile/check-status` - Davomat holatini tekshirish

### Davomat (Attendance)
- `POST /attendance/qr-scan` - QR kod skanerlash
- `GET /attendance/employee/{id}` - Xodim davomat tarixi
- `GET /attendance/daily/{date}` - Kunlik davomat
- `GET /attendance/status/{id}` - Xodim joriy holati
- `GET /attendance/report/monthly/{year}/{month}` - Oylik hisobot
- `GET /attendance/report/download/{year}/{month}` - Excel hisobotni yuklab olish

### Face ID
- `POST /face-id/register` - Yuz ma'lumotlarini ro'yxatdan o'tkazish
- `POST /face-id/recognize` - Yuzni tanish va davomat belgilash
- `GET /face-id/status/{employee_id}` - Face ID holati
- `DELETE /face-id/{employee_id}` - Face ID ma'lumotlarini o'chirish

### QR Kodlar
- `GET /qr/employee/{id}` - Xodim uchun QR kod yaratish
- `GET /qr/employee/{id}/image` - QR kod rasmi (PNG)
- `GET /qr/simple/{uuid}` - Oddiy QR kod

### Mobil API
- `POST /mobile/scan` - QR kod skanerlash (planshet uchun)
- `GET /mobile/status/{uuid}` - Xodim holati
- `GET /mobile/today-summary` - Bugungi statistika

## Ma'lumotlar tuzilishi

### Employee (Xodim)
```json
{
  "id": 1,
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
  "full_name": "Ahmadjon Karimov",
  "position": "MANAGER",
  "phone": "+998901234567",
  "photo": "/uploads/employee_photos/employee_1_abc123.jpg",
  "base_salary": "8000000.00",
  "is_active": true,
  "created_at": "2025-09-09T10:00:00Z"
}
```

### Attendance (Davomat)
```json
{
  "id": 1,
  "employee_id": 1,
  "check_type": "IN",
  "check_time": "2025-09-09T09:15:00Z",
  "is_late": true,
  "is_early_departure": false
}
```

## Lavozimlar (Positions)

- `MANAGER` - Menejer
- `DEVELOPER` - Dasturchi
- `DESIGNER` - Dizayner
- `HR` - HR mutaxassis
- `ACCOUNTANT` - Buxgalter
- `SALES` - Sotuvchi
- `MARKETING` - Marketing mutaxassisi
- `SUPPORT` - Qo'llab-quvvatlash
- `INTERN` - Stajer
- `OTHER` - Boshqa

## Face ID integratsiyasi

### Yuz ma'lumotlarini ro'yxatdan o'tkazish
```javascript
const formData = new FormData();
formData.append('photo', imageFile);

const response = await fetch(`/face-id/register`, {
  method: 'POST',
  body: formData
});

const result = await response.json();
if (response.ok) {
  console.log('Face ID muvaffaqiyatli ro\'yxatdan o\'tdi');
}
```

### Yuzni tanish va davomat
```javascript
const formData = new FormData();
formData.append('photo', imageFile);

const response = await fetch(`/face-id/recognize`, {
  method: 'POST', 
  body: formData
});

const result = await response.json();
if (response.ok) {
  console.log('Davomat belgilandi:', result);
}
```

### Rasm yuklash
```javascript
const formData = new FormData();
formData.append('file', imageFile);

const response = await fetch(`/employees/${employeeId}/photo`, {
  method: 'POST',
  body: formData
});

const result = await response.json();
if (response.ok) {
  console.log('Rasm URL:', result.photo_url);
}
```

### Rasm xususiyatlari

- **Ruxsat etilgan formatlar**: JPG, JPEG, PNG, GIF, WEBP
- **Maksimal o'lcham**: 5MB
- **Avtomatik optimizatsiya**: 800x800px gacha kichiklashtirish
- **URL struktura**: `/uploads/employee_photos/employee_{id}_{uuid}.jpg`
- **Avtomatik tozalash**: Eski rasm yangi yuklanganda o'chiriladi

## Hisobotlar

Oylik hisobotlar avtomatik ravishda Excel formatida yaratiladi:

- Umumiy ish kunlari
- Ishga kelgan kunlar
- Kechikgan kunlar
- Check-in/Check-out soni
- Davomat foizi

## Testing

```bash
# Serverni ishga tushiring
uvicorn app.main:app --reload

# Sample ma'lumotlar yaratish
python create_sample_data.py

# API endpointlarni test qilish uchun
# Swagger UI: http://localhost:8000/docs
# yoki Postman collection import qiling
```

## Production uchun sozlash

1. **Ma'lumotlar bazasi**: SQLite o'rniga PostgreSQL yoki MySQL ishlatish
2. **CORS**: `allow_origins=["*"]` o'rniga aniq domenlar
3. **Logging**: Proper logging konfiguratsiyasi
4. **Environment variables**: Sensitive ma'lumotlar uchun

## Fayllar tuzilishi

```
workly_app/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app entry point
│   ├── core/
│   │   ├── config.py          # Konfiguratsiya
│   │   └── database.py        # Ma'lumotlar bazasi ulanishi
│   ├── crud/                  # CRUD operatsiyalari
│   │   ├── attendance.py      # Davomat CRUD
│   │   └── employee.py        # Xodim CRUD
│   ├── models/                # SQLAlchemy modellari
│   │   ├── attendance.py      # Davomat modeli
│   │   └── employee.py        # Xodim modeli
│   ├── routers/               # API endpointlar
│   │   ├── attendance.py      # Davomat API
│   │   ├── employees.py       # Xodimlar API
│   │   ├── face_id.py         # Face ID API
│   │   ├── mobile.py          # Mobil API
│   │   └── statistics.py      # Statistika API
│   ├── schemas/               # Pydantic schemas
│   │   ├── attendance.py      # Davomat schemas
│   │   ├── employee.py        # Xodim schemas
│   │   └── face_id.py         # Face ID schemas
│   └── services/              # Business logic
│       ├── face_id.py         # Face ID servisi
│       ├── file_service.py    # Fayl boshqaruvi
│       ├── reports.py         # Hisobotlar
│       └── simple_face_id.py  # Sodda Face ID
├── face_data_simple/          # Face ID ma'lumotlari
├── uploads/                   # Yuklangan fayllar
├── requirements.txt           # Python paketlari
├── create_sample_data.py      # Sample ma'lumotlar yaratish
├── face_id.html              # Face ID test sahifasi
├── FACE_ID_TEST_GUIDE.md     # Face ID test qo'llanmasi
└── README.md                 # Loyiha haqida ma'lumot
```

## Muammolar va yechimlar

### Kechikish nazorati
- Check-in vaqti 9:00 dan keyin bo'lsa `is_late = True`
- Hisobotda alohida ustun ko'rsatiladi

### Erta ketish nazorati  
- Check-out vaqti 17:30 dan oldin bo'lsa `is_early_departure = True`
- Kun davomida ishlagan vaqt hisoblanadi

### Face ID xavfsizligi
- Yuz ma'lumotlari mahalliy saqlanadi (`face_data_simple/`)
- Har bir xodim uchun alohida fayl
- OpenCV va face_recognition kutubxonalari ishlatiladi

### Ma'lumotlar bazasi
- SQLite (development) / PostgreSQL (production)
- Async SQLAlchemy ishlatiladi
- Avtomatik migratsiya qo'llab-quvvatlanadi

### Sample ma'lumotlar
- 10 ta xodim (turli lavozimlarda)
- Oxirgi 30 kun uchun tasodifiy davomat
- Kechikish va erta ketish holatlari simulatsiya qilinadi

## Yordam

Savollar yoki muammolar uchun:
- GitHub Issues ochish
- Email: admin@workly.uz

---
**Workly Team** - 2025
