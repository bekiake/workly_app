"""
Утилиты для работы с timezone - Ташкентское время (UTC+5)
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

# Ташкентский timezone (UTC+5)
TASHKENT_TZ = timezone(timedelta(hours=5))


def get_tashkent_time() -> datetime:
    """Получить текущее время в Ташкентском timezone"""
    return datetime.now(TASHKENT_TZ)


def convert_to_tashkent(dt: datetime) -> datetime:
    """Конвертировать datetime в Ташкентское время"""
    if dt.tzinfo is None:
        # Если timezone не указан, считаем что это UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TASHKENT_TZ)


def get_tashkent_date():
    """Получить текущую дату в Ташкентском timezone"""
    return get_tashkent_time().date()


def format_tashkent_time(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Форматировать время в Ташкентском timezone"""
    if dt is None:
        dt = get_tashkent_time()
        dt = convert_to_tashkent(dt)
    else:
        if dt.tzinfo is None:
            # Если naive datetime, считаем что это уже Ташkentское время
            pass  # Ничего не делаем, время уже правильное
        else:
            # Если есть timezone, конвертируем в Ташkentское
            dt = convert_to_tashkent(dt)
    return dt.strftime(format_str)


def to_utc(tashkent_dt: datetime) -> datetime:
    """Конвертировать Ташкентское время в UTC для сохранения в базе"""
    if tashkent_dt.tzinfo is None:
        # Считаем что это Ташкентское время
        tashkent_dt = tashkent_dt.replace(tzinfo=TASHKENT_TZ)
    return tashkent_dt.astimezone(timezone.utc)


def get_tashkent_time_naive() -> datetime:
    """Получить текущее время в Ташkentском timezone но без timezone info (naive datetime)"""
    return get_tashkent_time().replace(tzinfo=None)
