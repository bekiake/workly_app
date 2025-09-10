# Workly - Xodimlar Davomat Nazorati Tizimi 📱

## Loyiha haqida

Workly - bu ishxona xodimlarining kelish-ketish vaqtlarini QR kod orqali nazorat qilish uchun mo'ljallangan backend API tizimi. 

### Asosiy xususiyatlar:

- 🔐 **QR kod orqali autentifikatsiya** - Har bir xodim uchun noyob UUID asosida QR kod
- ⏰ **Vaqt nazorati** - Kelish/ketish vaqtlarini aniq yozib olish
- 📊 **Hisobotlar** - Oylik Excel hisobotlari
- 📱 **Mobil API** - Planshet ilovasi uchun optimallashtirilgan
- 🕘 **Kechikish nazorati** - 9:00 dan keyin kelganlarni avtomatik aniqlash

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

### 4. Ma'lumotlar bazasini sozlash
```bash
python migrate.py
```

### 5. Sample ma'lumotlar yaratish (ixtiyoriy)
```bash
python create_sample_data.py
```

## Ishga tushirish

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API dokumentatsiya: http://localhost:8000/docs

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
  "position": "manager",
  "phone": "+998901234567",
  "email": "ahmadjon@workly.uz",
  "qr_code": "123e4567-e89b-12d3-a456-426614174000",
  "is_active": true,
  "created_at": "2025-09-09T10:00:00Z"
}
```

### Attendance (Davomat)
```json
{
  "id": 1,
  "employee_id": 1,
  "check_type": "in",
  "check_time": "2025-09-09T09:15:00Z",
  "location": "Ofis",
  "is_late": true
}
```

## Lavozimlar (Positions)

- `manager` - Menejer
- `developer` - Dasturchi
- `designer` - Dizayner
- `hr` - HR mutaxassis
- `accountant` - Buxgalter
- `sales` - Sotuvchi
- `marketing` - Marketing
- `support` - Qo'llab-quvvatlash
- `intern` - Stajer
- `other` - Boshqa

## Mobil ilova integratsiyasi

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

# Boshqa terminalda test ishga tushiring
python test_api.py
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
│   ├── core/
│   │   ├── config.py          # Konfiguratsiya
│   │   └── database.py        # Ma'lumotlar bazasi ulanishi
│   ├── crud/                  # CRUD operatsiyalari
│   ├── models/                # SQLAlchemy modellari
│   ├── routers/               # API endpoint lar
│   ├── schemas/               # Pydantic schemas
│   └── services/              # Business logic
├── requirements.txt           # Python paketlari
├── migrate.py                # Database migration
├── create_sample_data.py     # Sample ma'lumotlar
└── test_api.py               # API testlari
```

## Muammolar va yechimlar

### Kech amalga oshirilishi
- Check-in vaqti 9:00 dan keyin bo'lsa `is_late = True`
- Hisobotda alohida ustun

### Takroriy check-in/out oldini olish
- Bir kunda bir xil harakatni takrorlash mumkin emas
- API avtomatik tekshiradi

### QR kod xavfsizligi
- UUID asosida noyob kodlar
- Har bir xodim uchun alohida

## Yordam

Savollar yoki muammolar uchun:
- GitHub Issues ochish
- Email: admin@workly.uz

---
**Workly Team** - 2025
