import os
import uuid
import aiofiles
from typing import Optional
from fastapi import UploadFile, HTTPException
from PIL import Image
import io

# Upload katalogini yaratish
UPLOAD_DIR = "uploads/employee_photos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Ruxsat etilgan rasm formatlari
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

async def save_employee_photo(file: UploadFile, employee_id: int) -> str:
    """
    Xodim rasmini saqlash va URL qaytarish
    
    Args:
        file: Upload qilingan fayl
        employee_id: Xodim ID si
    
    Returns:
        Saqlangan faylning URL manzili
    """
    
    # Fayl formatini tekshirish
    if not file.filename:
        raise HTTPException(status_code=400, detail="Fayl nomi ko'rsatilmagan")
    
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Noto'g'ri fayl formati. Ruxsat etilgan: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Fayl o'lchamini tekshirish
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"Fayl juda katta. Maksimal o'lcham: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Fayl nomini yaratish
    unique_filename = f"employee_{employee_id}_{uuid.uuid4().hex[:8]}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        # Rasmni optimizatsiya qilish
        image = Image.open(io.BytesIO(contents))
        
        # Rasmni kichiklashtirish (agar katta bo'lsa)
        max_size = (800, 800)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # RGBA formatini RGB ga o'girish (agar kerak bo'lsa)
        if image.mode in ("RGBA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            image = background
        
        # Faylni saqlash
        image.save(file_path, "JPEG", quality=85, optimize=True)
        
        # URL yaratish
        file_url = f"/uploads/employee_photos/{unique_filename}"
        return file_url
        
    except Exception as e:
        # Xato bo'lsa faylni o'chirish
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Rasmni saqlashda xato: {str(e)}")

async def delete_employee_photo(photo_url: str) -> bool:
    """
    Eski rasmni o'chirish
    
    Args:
        photo_url: Rasm URL manzili
    
    Returns:
        O'chirish muvaffaqiyatlimi
    """
    try:
        if photo_url and photo_url.startswith("/uploads/employee_photos/"):
            filename = photo_url.split("/")[-1]
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        return False
    except Exception:
        return False

def get_photo_full_path(photo_url: str) -> Optional[str]:
    """
    Rasm URL dan to'liq fayl yo'lini olish
    
    Args:
        photo_url: Rasm URL manzili
    
    Returns:
        To'liq fayl yo'li yoki None
    """
    if photo_url and photo_url.startswith("/uploads/employee_photos/"):
        filename = photo_url.split("/")[-1]
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        if os.path.exists(file_path):
            return file_path
    
    return None
