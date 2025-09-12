import math
from typing import Tuple
from datetime import datetime, timedelta

# Координаты офиса (замените на реальные)
OFFICE_LATITUDE = 41.304502
OFFICE_LONGITUDE = 69.321159
OFFICE_RADIUS_METERS = 200  # Радиус в метрах для проверки


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Вычисляет расстояние между двумя точками на земле в метрах
    Использует формулу Haversine
    """
    # Радиус Земли в метрах
    R = 6371000
    
    # Преобразуем градусы в радианы
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Формула Haversine
    a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) * math.sin(delta_lon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Расстояние в метрах
    distance = R * c
    return distance


def is_at_office(latitude: float, longitude: float) -> Tuple[bool, float]:
    """
    Проверяет, находится ли пользователь в офисе
    Возвращает (в_офисе: bool, расстояние_в_метрах: float)
    """
    distance = calculate_distance(
        OFFICE_LATITUDE, OFFICE_LONGITUDE,
        latitude, longitude
    )
    
    is_in_office = distance <= OFFICE_RADIUS_METERS
    return is_in_office, distance


def validate_live_location_security(location_data) -> Tuple[bool, str]:
    """
    Дополнительная проверка безопасности Live Location
    """
    # Проверяем основные координаты на подозрительные значения
    lat = location_data.latitude
    lon = location_data.longitude
    
    # Проверка на точные координаты (возможно поддельные)
    if lat == int(lat) and lon == int(lon):
        return False, "Подозрительно точные координаты"
    
    # Проверка на популярные поддельные координаты
    fake_coords = [
        (0.0, 0.0),  # Null Island
        (37.7749, -122.4194),  # San Francisco (популярные в эмуляторах)
        (40.7128, -74.0060),   # New York
    ]
    
    for fake_lat, fake_lon in fake_coords:
        if abs(lat - fake_lat) < 0.001 and abs(lon - fake_lon) < 0.001:
            return False, "Обнаружены подозрительные координаты"
    
    # Проверка на слишком высокую точность (возможно GPS spoofing)
    if hasattr(location_data, 'horizontal_accuracy'):
        if location_data.horizontal_accuracy and location_data.horizontal_accuracy < 3:
            return False, "Подозрительно высокая точность GPS"
    
    return True, "OK"


def format_distance(distance_meters: float) -> str:
    """Форматирует расстояние для отображения пользователю"""
    if distance_meters < 1000:
        return f"{distance_meters:.0f} м"
    else:
        return f"{distance_meters/1000:.1f} км"


def is_location_realistic(latitude: float, longitude: float) -> bool:
    """
    Проверяет, являются ли координаты реалистичными для данного региона
    """
    # Примерные границы для Узбекистана (можете изменить под свой регион)
    MIN_LAT, MAX_LAT = 37.0, 46.0
    MIN_LON, MAX_LON = 56.0, 74.0
    
    if not (MIN_LAT <= latitude <= MAX_LAT):
        return False
    if not (MIN_LON <= longitude <= MAX_LON):
        return False
        
    return True