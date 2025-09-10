# 🎭 Face ID Test Qo'llanmasi

## 📋 Oldindan tayyorlik:

### 1. Server ishga tushirish:
```bash
cd d:\workly_app
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. HTML faylni ochish:
Browserda quyidagi URL ni oching:
```
file:///d:/workly_app/face_id.html
```

## 🧪 Test qadamlari:

### QADAM 1: Xodimning yuzini ro'yxatga olish

1. **"Ro'yxatga olish" tab**ni bosing
2. **Dropdown**dan xodimni tanlang
3. **"Kamerani yoqish"** tugmasini bosing
4. Browser **ruxsat so'raganda "Allow"** bosing
5. **Yuzingizni kameraga qarating**:
   - To'g'ridan-to'g'ri qarang
   - 1-2 metr masofada turing
   - Yetarli yorug'lik bo'lsin
   - Ko'zoynak/niqob taqmang
6. **"Rasmga olish"** tugmasini bosing
7. **Preview**da rasmni tekshiring
8. **"Ro'yxatga olish"** tugmasini bosing

**Kutilgan natija**: ✅ "Yuz ma'lumotlari muvaffaqiyatli saqlandi"

### QADAM 2: Davomat belgilash (Kelish)

1. **"Davomat belgilash" tab**ni bosing
2. **Harakat turi**: "Kelish" tanlang
3. **"Kamerani yoqish"** tugmasini bosing
4. **Yuzingizni kameraga qarating**
5. **"Rasmga olish"** tugmasini bosing
6. **"Davomat belgilash"** tugmasini bosing

**Kutilgan natija**: ✅ "Davomat muvaffaqiyatli belgilandi" + ishonch %

### QADAM 3: Dublikat test (Yana kelish)

1. **Yuqoridagi qadamni qaytaring**
2. **Yana "Kelish" ni tanlang**
3. **Rasmga oling va yuborish**

**Kutilgan natija**: ❌ "Siz bugun allaqachon kelgansiz deb belgilangansiz"

### QADAM 4: Ketish test

1. **Harakat turi**: "Ketish" tanlang
2. **Rasmga oling va yuborish**

**Kutilgan natija**: ✅ "Davomat muvaffaqiyatli belgilandi" + ishonch %

### QADAM 5: Statistika ko'rish

1. **"Statistika" tab**ni bosing
2. **"Statistikani yuklash"** tugmasini bosing

**Kutilgan natija**: 
- Ro'yxatga olingan xodimlar: 1
- Jami yuzlar: 1  
- Xodim tafsiloti ko'rinadi

## 🔧 Debugging:

### Browser Console:
`F12` -> `Console` tab da xatoliklarni ko'ring

### Server Logs:
Terminal da server loglarini kuzating

### API Test:
```bash
# Healthcheck
curl http://localhost:8000/face-id/health

# Statistics  
curl http://localhost:8000/face-id/statistics
```

## 📊 Kutilgan oqim:

```
1. Ro'yxatga olish
   ↓
2. Kelish davomat
   ↓  
3. Dublikat test (xato)
   ↓
4. Ketish davomat
   ↓
5. Statistika
```

## ⚠️ Muammolar va yechimlar:

| Muammo | Yechim |
|--------|--------|
| Kamera ishlamaydi | Browser ruxsat bering |
| Yuz topilmadi | Yaxshi yorug'lik, to'g'ri burchak |
| Server ulanmaydi | uvicorn ni tekshiring |
| Xodim topilmadi | Database da xodim borligini tekshiring |

## 🎯 Muvaffaqiyat ko'rsatkichlari:

- ✅ Kamera yoqildi
- ✅ Rasm olindi  
- ✅ Yuz ro'yxatga olindi
- ✅ Davomat belgilandi
- ✅ Dublikat oldini olindi
- ✅ Statistika ko'rsatildi

Har bir qadamda browser **Console** va server **logs**ni kuzatib boring!
