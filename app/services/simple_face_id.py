import cv2
import numpy as np
import os
import pickle
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
import hashlib

class SimpleFaceIDService:
    """
    OpenCV asosida oddiy Face ID tizimi
    dlib muammosi uchun alternative yechim
    """
    
    def __init__(self):
        self.face_encodings_path = "face_data_simple"
        self.known_faces = {}  # {employee_id: [face_features]}
        self.known_names = {}  # {employee_id: full_name}
        self.face_cascade = None
        self.face_templates = {}  # {employee_id: [face_images]}
        self.tolerance = 0.3  # Simple face recognition tolerance
        self.max_faces_per_employee = 3  # Har bir xodim uchun maksimal yuz soni
        
        # Face data papkasini yaratish
        os.makedirs(self.face_encodings_path, exist_ok=True)
        
        # OpenCV face classifier yuklash
        self.load_face_cascade()
        
        # Saqlangan yuzlarni yuklash
        self.load_known_faces()
    
    def load_face_cascade(self):
        """OpenCV face cascade yuklash"""
        try:
            # OpenCV bilan birga keluvchi face cascade
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            
            if self.face_cascade.empty():
                print("⚠️ Face cascade yuklashda muammo")
            else:
                print("✅ OpenCV face cascade yuklandi")
                
        except Exception as e:
            print(f"❌ Face cascade yuklashda xatolik: {e}")
    
    def save_known_faces(self):
        """Tanilgan yuzlarni faylga saqlash"""
        data = {
            'faces': self.known_faces,
            'names': self.known_names,
            'templates': self.face_templates
        }
        with open(f"{self.face_encodings_path}/known_faces.pkl", "wb") as f:
            pickle.dump(data, f)
    
    def load_known_faces(self):
        """Saqlangan yuzlarni yuklash"""
        try:
            with open(f"{self.face_encodings_path}/known_faces.pkl", "rb") as f:
                data = pickle.load(f)
                self.known_faces = data.get('faces', {})
                self.known_names = data.get('names', {})
                self.face_templates = data.get('templates', {})
            print(f"✅ {len(self.known_faces)} xodimning yuz ma'lumotlari yuklandi")
        except FileNotFoundError:
            print("📁 Yuz ma'lumotlari fayli topilmadi. Yangi fayl yaratiladi.")
            self.known_faces = {}
            self.known_names = {}
            self.face_templates = {}
    
    def extract_face_features(self, image_array: np.ndarray) -> Dict[str, Any]:
        """
        Yuzdan oddiy features ni ajratib olish
        OpenCV bilan basic feature extraction
        """
        if self.face_cascade is None:
            return None
            
        # Yuzlarni topish
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(50, 50)
        )
        
        if len(faces) == 0:
            return None
            
        if len(faces) > 1:
            # Eng katta yuzni tanlash
            areas = [(w * h, i) for i, (x, y, w, h) in enumerate(faces)]
            largest_face_idx = max(areas)[1]
            x, y, w, h = faces[largest_face_idx]
        else:
            x, y, w, h = faces[0]
        
        # Yuzni crop qilish va resize qilish
        face_roi = gray[y:y+h, x:x+w]
        face_resized = cv2.resize(face_roi, (100, 100))
        
        # Basic features
        features = {
            'histogram': cv2.calcHist([face_resized], [0], None, [256], [0, 256]).flatten(),
            'mean_intensity': np.mean(face_resized),
            'std_intensity': np.std(face_resized),
            'face_template': face_resized.flatten(),
            'face_hash': hashlib.md5(face_resized.tobytes()).hexdigest(),
            'dimensions': (w, h),
            'position': (x, y)
        }
        
        return features
    
    def compare_faces(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """
        Ikki yuz o'rtasidagi o'xshashlikni hisoblash
        0.0 - bir xil, 1.0 - butunlay farq
        """
        try:
            # Histogram taqqoslash
            hist_corr = cv2.compareHist(
                features1['histogram'].astype(np.float32), 
                features2['histogram'].astype(np.float32), 
                cv2.HISTCMP_CORREL
            )
            
            # Template matching
            template_diff = np.mean(np.abs(
                features1['face_template'].astype(np.float32) - 
                features2['face_template'].astype(np.float32)
            )) / 255.0
            
            # Intensity statistics
            mean_diff = abs(features1['mean_intensity'] - features2['mean_intensity']) / 255.0
            std_diff = abs(features1['std_intensity'] - features2['std_intensity']) / 255.0
            
            # Combined score (lower is better)
            distance = (
                (1 - hist_corr) * 0.4 +  # Histogram similarity (inverted)
                template_diff * 0.4 +     # Template difference
                mean_diff * 0.1 +         # Mean intensity difference
                std_diff * 0.1            # Std intensity difference
            )
            
            return min(1.0, max(0.0, distance))
            
        except Exception as e:
            print(f"Yuzlarni taqqoslashda xatolik: {e}")
            return 1.0  # Max distance if error
    
    def register_employee_face(self, employee_id: int, employee_name: str, 
                             image_data: bytes) -> dict:
        """Xodimning yuzini ro'yxatga olish"""
        try:
            # Base64 dan image ga o'tkazish
            if image_data.startswith(b'data:image'):
                image_data = image_data.split(b',')[1]
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            image_array = np.array(image)
            
            # Yuz features ni ajratib olish
            features = self.extract_face_features(image_array)
            
            if features is None:
                return {
                    "success": False,
                    "message": "Rasmda yuz topilmadi. Iltimos, aniqroq rasm yuboring.",
                    "faces_found": 0
                }
            
            # YAXSHILASHTIRILGAN TEKSHIRUV: 
            # 1. Barcha mavjud xodimlar orasida bu yuz bormi?
            # 2. Agar boshqa xodimga tegishli bo'lsa, xatolik qaytarish
            for existing_emp_id, existing_features_list in self.known_faces.items():
                for existing_features in existing_features_list:
                    distance = self.compare_faces(existing_features, features)
                    if distance < self.tolerance:
                        if existing_emp_id == employee_id:
                            return {
                                "success": False,
                                "message": "Bu yuz allaqachon ushbu xodim uchun ro'yxatga olingan.",
                                "similarity": f"{(1-distance)*100:.1f}%",
                                "duplicate_for": "same_employee"
                            }
                        else:
                            existing_name = self.known_names.get(existing_emp_id, f"ID: {existing_emp_id}")
                            return {
                                "success": False,
                                "message": f"Bu yuz boshqa xodimga ({existing_name}) tegishli. Bir xil yuzni ikki xodimga bog'lab bo'lmaydi.",
                                "similarity": f"{(1-distance)*100:.1f}%",
                                "duplicate_for": "different_employee",
                                "existing_employee_id": existing_emp_id,
                                "existing_employee_name": existing_name
                            }
            
            # Xodimning mavjud yuzlarini tekshirish
            if employee_id not in self.known_faces:
                self.known_faces[employee_id] = []
                self.face_templates[employee_id] = []
            
            # Maksimal yuz soni tekshiruvi
            current_face_count = len(self.known_faces[employee_id])
            if current_face_count >= self.max_faces_per_employee:
                return {
                    "success": False,
                    "message": f"Xodim uchun maksimal {self.max_faces_per_employee} ta yuz ruxsat etiladi. Avval eski yuzlarni o'chiring.",
                    "current_faces": current_face_count,
                    "max_allowed": self.max_faces_per_employee
                }
            
            # Yangi yuzni qo'shish
            self.known_faces[employee_id].append(features)
            self.known_names[employee_id] = employee_name
            self.face_templates[employee_id].append(image_array)
            
            # Faylga saqlash
            self.save_known_faces()
            
            # Xodim rasmini ham saqlash
            employee_dir = f"{self.face_encodings_path}/employee_{employee_id}"
            os.makedirs(employee_dir, exist_ok=True)
            
            face_count = len(self.known_faces[employee_id])
            image_path = f"{employee_dir}/face_{face_count}.jpg"
            image.save(image_path)
            
            return {
                "success": True,
                "message": f"{employee_name} ning yuz ma'lumotlari muvaffaqiyatli saqlandi.",
                "employee_id": employee_id,
                "face_count": face_count,
                "max_faces": self.max_faces_per_employee,
                "image_saved": image_path,
                "method": "OpenCV Simple Face Recognition",
                "can_add_more": face_count < self.max_faces_per_employee
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Yuzni ro'yxatga olishda xatolik: {str(e)}",
                "error": str(e)
            }
    
    def recognize_face(self, image_data: bytes) -> dict:
        """Yuzni tanish va xodimni aniqlash"""
        try:
            # Base64 dan image ga o'tkazish
            if image_data.startswith(b'data:image'):
                image_data = image_data.split(b',')[1]
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            image_array = np.array(image)
            
            # Yuz features ni ajratib olish
            unknown_features = self.extract_face_features(image_array)
            
            if unknown_features is None:
                return {
                    "success": False,
                    "message": "Rasmda yuz topilmadi.",
                    "employee_id": None,
                    "confidence": 0
                }
            
            # Eng yaxshi mos keluvchini topish
            best_match_id = None
            best_distance = float('inf')
            
            for employee_id, face_features_list in self.known_faces.items():
                for face_features in face_features_list:
                    distance = self.compare_faces(face_features, unknown_features)
                    
                    if distance < best_distance:
                        best_distance = distance
                        best_match_id = employee_id
            
            # Threshold check (0.5 = 50% similarity required)
            if best_match_id and best_distance < 0.5:
                confidence = (1 - best_distance) * 100
                employee_name = self.known_names.get(best_match_id, "Noma'lum")
                
                return {
                    "success": True,
                    "message": f"Xodim tanildi: {employee_name}",
                    "employee_id": best_match_id,
                    "employee_name": employee_name,
                    "confidence": f"{confidence:.1f}%",
                    "distance": best_distance,
                    "method": "OpenCV Simple Face Recognition"
                }
            else:
                return {
                    "success": False,
                    "message": "Yuz tanilmadi. Ro'yxatda yo'q yoki o'xshashlik past.",
                    "employee_id": None,
                    "confidence": f"{(1-best_distance)*100:.1f}%" if best_distance != float('inf') else "0%",
                    "best_distance": best_distance if best_distance != float('inf') else None
                }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Yuzni tanishda xatolik: {str(e)}",
                "employee_id": None,
                "confidence": 0,
                "error": str(e)
            }
    
    def get_employee_faces_count(self, employee_id: int) -> int:
        """Xodimning ro'yxatga olingan yuzlari sonini olish"""
        return len(self.known_faces.get(employee_id, []))
    
    def delete_employee_faces(self, employee_id: int) -> dict:
        """Xodimning barcha yuz ma'lumotlarini o'chirish"""
        try:
            if employee_id in self.known_faces:
                employee_name = self.known_names.get(employee_id, "Noma'lum")
                face_count = len(self.known_faces[employee_id])
                
                # Ma'lumotlarni o'chirish
                del self.known_faces[employee_id]
                if employee_id in self.known_names:
                    del self.known_names[employee_id]
                if employee_id in self.face_templates:
                    del self.face_templates[employee_id]
                
                # Fayl va papkani o'chirish
                employee_dir = f"{self.face_encodings_path}/employee_{employee_id}"
                if os.path.exists(employee_dir):
                    import shutil
                    shutil.rmtree(employee_dir)
                
                # Saqlash
                self.save_known_faces()
                
                return {
                    "success": True,
                    "message": f"{employee_name} ning {face_count} ta yuz ma'lumoti o'chirildi.",
                    "deleted_faces": face_count
                }
            else:
                return {
                    "success": False,
                    "message": "Bu xodimning yuz ma'lumotlari topilmadi.",
                    "deleted_faces": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Yuz ma'lumotlarini o'chirishda xatolik: {str(e)}",
                "error": str(e)
            }
    
    def get_employee_faces_count(self, employee_id: int) -> int:
        """Xodimning ro'yxatga olingan yuzlari sonini olish"""
        return len(self.known_faces.get(employee_id, []))
    
    def can_add_more_faces(self, employee_id: int) -> dict:
        """Xodim uchun yana yuz qo'shish mumkinligini tekshirish"""
        current_count = self.get_employee_faces_count(employee_id)
        can_add = current_count < self.max_faces_per_employee
        
        return {
            "can_add": can_add,
            "current_faces": current_count,
            "max_faces": self.max_faces_per_employee,
            "remaining_slots": self.max_faces_per_employee - current_count if can_add else 0
        }
    
    def check_face_exists_for_other_employee(self, features, exclude_employee_id: int = None) -> dict:
        """Berilgan yuz boshqa xodimga tegishli emasligini tekshirish"""
        for emp_id, feature_list in self.known_faces.items():
            if exclude_employee_id and emp_id == exclude_employee_id:
                continue
                
            for existing_features in feature_list:
                distance = self.compare_faces(existing_features, features)
                if distance < self.tolerance:
                    return {
                        "exists": True,
                        "employee_id": emp_id,
                        "employee_name": self.known_names.get(emp_id, f"ID: {emp_id}"),
                        "similarity": f"{(1-distance)*100:.1f}%",
                        "distance": distance
                    }
        
        return {"exists": False}

    def get_statistics(self) -> dict:
        """Face ID tizimi statistikalari"""
        total_employees = len(self.known_faces)
        total_faces = sum(len(faces) for faces in self.known_faces.values())
        
        employee_stats = []
        for emp_id, faces in self.known_faces.items():
            face_count = len(faces)
            employee_stats.append({
                "employee_id": emp_id,
                "employee_name": self.known_names.get(emp_id, "Noma'lum"),
                "face_count": face_count,
                "can_add_more": face_count < self.max_faces_per_employee,
                "remaining_slots": self.max_faces_per_employee - face_count
            })
        
        return {
            "total_employees": total_employees,
            "total_faces": total_faces,
            "average_faces_per_employee": total_faces / total_employees if total_employees > 0 else 0,
            "tolerance": self.tolerance,
            "max_faces_per_employee": self.max_faces_per_employee,
            "method": "OpenCV Simple Face Recognition",
            "features": ["Histogram comparison", "Template matching", "Intensity statistics"],
            "employee_details": employee_stats,
            "system_limits": {
                "max_faces_per_employee": self.max_faces_per_employee,
                "face_recognition_tolerance": self.tolerance
            }
        }
    
    def test_system(self) -> dict:
        """Tizimni test qilish"""
        try:
            test_results = {
                "face_cascade_loaded": self.face_cascade is not None and not self.face_cascade.empty(),
                "data_directory_exists": os.path.exists(self.face_encodings_path),
                "employees_registered": len(self.known_faces),
                "total_face_samples": sum(len(faces) for faces in self.known_faces.values()),
                "system_ready": True
            }
            
            return {
                "success": True,
                "message": "Face ID tizimi test muvaffaqiyatli",
                "test_results": test_results
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Tizim testida xatolik: {str(e)}",
                "error": str(e)
            }

# Global Simple Face ID servis instance
simple_face_service = SimpleFaceIDService()
