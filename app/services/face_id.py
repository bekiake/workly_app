# import cv2
# import face_recognition
# import numpy as np
# import os
# import pickle
# from typing import List, Optional, Tuple
# from datetime import datetime
# import base64
# from io import BytesIO
# from PIL import Image

# class FaceIDService:
#     """Face ID tanish va davomat tizimi"""
    
#     def __init__(self):
#         self.face_encodings_path = "face_data"
#         self.known_faces = {}  # {employee_id: [face_encodings]}
#         self.known_names = {}  # {employee_id: full_name}
#         self.tolerance = 0.6  # Tanish sezgirligi
        
#         # Face data papkasini yaratish
#         os.makedirs(self.face_encodings_path, exist_ok=True)
        
#         # Saqlangan yuzlarni yuklash
#         self.load_known_faces()
    
#     def save_known_faces(self):
#         """Tanilgan yuzlarni faylga saqlash"""
#         data = {
#             'faces': self.known_faces,
#             'names': self.known_names
#         }
#         with open(f"{self.face_encodings_path}/known_faces.pkl", "wb") as f:
#             pickle.dump(data, f)
    
#     def load_known_faces(self):
#         """Saqlangan yuzlarni yuklash"""
#         try:
#             with open(f"{self.face_encodings_path}/known_faces.pkl", "rb") as f:
#                 data = pickle.load(f)
#                 self.known_faces = data.get('faces', {})
#                 self.known_names = data.get('names', {})
#             print(f"✅ {len(self.known_faces)} xodimning yuz ma'lumotlari yuklandi")
#         except FileNotFoundError:
#             print("📁 Yuz ma'lumotlari fayli topilmadi. Yangi fayl yaratiladi.")
#             self.known_faces = {}
#             self.known_names = {}
    
#     def register_employee_face(self, employee_id: int, employee_name: str, 
#                              image_data: bytes) -> dict:
#         """Xodimning yuzini ro'yxatga olish"""
#         try:
#             # Base64 dan image ga o'tkazish
#             if image_data.startswith(b'data:image'):
#                 # Data URL formatini tozalash
#                 image_data = image_data.split(b',')[1]
            
#             # Base64 decode
#             image_bytes = base64.b64decode(image_data)
            
#             # PIL Image yaratish
#             image = Image.open(BytesIO(image_bytes))
            
#             # RGB formatga o'tkazish
#             if image.mode != 'RGB':
#                 image = image.convert('RGB')
            
#             # Numpy array ga o'tkazish
#             image_array = np.array(image)
            
#             # Yuzlarni topish
#             face_locations = face_recognition.face_locations(image_array)
            
#             if not face_locations:
#                 return {
#                     "success": False,
#                     "message": "Rasmda yuz topilmadi. Iltimos, aniqroq rasm yuboring.",
#                     "faces_found": 0
#                 }
            
#             if len(face_locations) > 1:
#                 return {
#                     "success": False,
#                     "message": "Rasmda bir nechta yuz topildi. Faqat bitta yuz bo'lishi kerak.",
#                     "faces_found": len(face_locations)
#                 }
            
#             # Yuz encoding yaratish
#             face_encodings = face_recognition.face_encodings(image_array, face_locations)
            
#             if not face_encodings:
#                 return {
#                     "success": False,
#                     "message": "Yuz ma'lumotlarini olishda xatolik yuz berdi.",
#                     "faces_found": len(face_locations)
#                 }
            
#             face_encoding = face_encodings[0]
            
#             # Xodimning mavjud yuzlarini tekshirish
#             if employee_id not in self.known_faces:
#                 self.known_faces[employee_id] = []
            
#             # Bir xil yuzni qayta qo'shmaslik uchun tekshirish
#             for existing_encoding in self.known_faces[employee_id]:
#                 distance = face_recognition.face_distance([existing_encoding], face_encoding)[0]
#                 if distance < self.tolerance:
#                     return {
#                         "success": False,
#                         "message": "Bu yuz allaqachon ro'yxatga olingan.",
#                         "similarity": f"{(1-distance)*100:.1f}%"
#                     }
            
#             # Yangi yuzni qo'shish
#             self.known_faces[employee_id].append(face_encoding)
#             self.known_names[employee_id] = employee_name
            
#             # Faylga saqlash
#             self.save_known_faces()
            
#             # Xodim rasmini ham saqlash
#             employee_dir = f"{self.face_encodings_path}/employee_{employee_id}"
#             os.makedirs(employee_dir, exist_ok=True)
            
#             face_count = len(self.known_faces[employee_id])
#             image_path = f"{employee_dir}/face_{face_count}.jpg"
#             image.save(image_path)
            
#             return {
#                 "success": True,
#                 "message": f"{employee_name} ning yuz ma'lumotlari muvaffaqiyatli saqlandi.",
#                 "employee_id": employee_id,
#                 "face_count": face_count,
#                 "image_saved": image_path
#             }
            
#         except Exception as e:
#             return {
#                 "success": False,
#                 "message": f"Yuzni ro'yxatga olishda xatolik: {str(e)}",
#                 "error": str(e)
#             }
    
#     def recognize_face(self, image_data: bytes) -> dict:
#         """Yuzni tanish va xodimni aniqlash"""
#         try:
#             # Base64 dan image ga o'tkazish
#             if image_data.startswith(b'data:image'):
#                 image_data = image_data.split(b',')[1]
            
#             image_bytes = base64.b64decode(image_data)
#             image = Image.open(BytesIO(image_bytes))
            
#             if image.mode != 'RGB':
#                 image = image.convert('RGB')
            
#             image_array = np.array(image)
            
#             # Yuzlarni topish
#             face_locations = face_recognition.face_locations(image_array)
            
#             if not face_locations:
#                 return {
#                     "success": False,
#                     "message": "Rasmda yuz topilmadi.",
#                     "employee_id": None,
#                     "confidence": 0
#                 }
            
#             # Har bir topilgan yuz uchun
#             results = []
            
#             for face_location in face_locations:
#                 # Yuz encoding olish
#                 face_encodings = face_recognition.face_encodings(image_array, [face_location])
                
#                 if not face_encodings:
#                     continue
                
#                 unknown_encoding = face_encodings[0]
                
#                 # Eng yaxshi mos keluvchini topish
#                 best_match_id = None
#                 best_distance = float('inf')
                
#                 for employee_id, known_encodings in self.known_faces.items():
#                     for known_encoding in known_encodings:
#                         distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]
                        
#                         if distance < self.tolerance and distance < best_distance:
#                             best_distance = distance
#                             best_match_id = employee_id
                
#                 if best_match_id:
#                     confidence = (1 - best_distance) * 100
#                     employee_name = self.known_names.get(best_match_id, "Noma'lum")
                    
#                     results.append({
#                         "success": True,
#                         "message": f"Xodim tanildi: {employee_name}",
#                         "employee_id": best_match_id,
#                         "employee_name": employee_name,
#                         "confidence": f"{confidence:.1f}%",
#                         "distance": best_distance
#                     })
#                 else:
#                     results.append({
#                         "success": False,
#                         "message": "Yuz tanilmadi. Ro'yxatda yo'q.",
#                         "employee_id": None,
#                         "confidence": 0
#                     })
            
#             # Eng yaxshi natijani qaytarish
#             if results:
#                 best_result = max(results, key=lambda x: float(x.get('confidence', '0').replace('%', '')))
#                 return best_result
#             else:
#                 return {
#                     "success": False,
#                     "message": "Yuz ma'lumotlarini olishda xatolik.",
#                     "employee_id": None,
#                     "confidence": 0
#                 }
            
#         except Exception as e:
#             return {
#                 "success": False,
#                 "message": f"Yuzni tanishda xatolik: {str(e)}",
#                 "employee_id": None,
#                 "confidence": 0,
#                 "error": str(e)
#             }
    
#     def get_employee_faces_count(self, employee_id: int) -> int:
#         """Xodimning ro'yxatga olingan yuzlari sonini olish"""
#         return len(self.known_faces.get(employee_id, []))
    
#     def delete_employee_faces(self, employee_id: int) -> dict:
#         """Xodimning barcha yuz ma'lumotlarini o'chirish"""
#         try:
#             if employee_id in self.known_faces:
#                 employee_name = self.known_names.get(employee_id, "Noma'lum")
#                 face_count = len(self.known_faces[employee_id])
                
#                 # Ma'lumotlarni o'chirish
#                 del self.known_faces[employee_id]
#                 if employee_id in self.known_names:
#                     del self.known_names[employee_id]
                
#                 # Fayl va papkani o'chirish
#                 employee_dir = f"{self.face_encodings_path}/employee_{employee_id}"
#                 if os.path.exists(employee_dir):
#                     import shutil
#                     shutil.rmtree(employee_dir)
                
#                 # Saqlash
#                 self.save_known_faces()
                
#                 return {
#                     "success": True,
#                     "message": f"{employee_name} ning {face_count} ta yuz ma'lumoti o'chirildi.",
#                     "deleted_faces": face_count
#                 }
#             else:
#                 return {
#                     "success": False,
#                     "message": "Bu xodimning yuz ma'lumotlari topilmadi.",
#                     "deleted_faces": 0
#                 }
                
#         except Exception as e:
#             return {
#                 "success": False,
#                 "message": f"Yuz ma'lumotlarini o'chirishda xatolik: {str(e)}",
#                 "error": str(e)
#             }
    
#     def get_statistics(self) -> dict:
#         """Face ID tizimi statistikalari"""
#         total_employees = len(self.known_faces)
#         total_faces = sum(len(faces) for faces in self.known_faces.values())
        
#         employee_stats = []
#         for emp_id, faces in self.known_faces.items():
#             employee_stats.append({
#                 "employee_id": emp_id,
#                 "employee_name": self.known_names.get(emp_id, "Noma'lum"),
#                 "face_count": len(faces)
#             })
        
#         return {
#             "total_employees": total_employees,
#             "total_faces": total_faces,
#             "average_faces_per_employee": total_faces / total_employees if total_employees > 0 else 0,
#             "tolerance": self.tolerance,
#             "employee_details": employee_stats
#         }

# # Global Face ID servis instance
# face_service = FaceIDService()
