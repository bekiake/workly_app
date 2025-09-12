import logging
from datetime import datetime
from typing import Callable, Dict, Any, Awaitable, Union

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update, User


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования всех действий пользователей"""
    
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery, Update], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery, Update],
        data: Dict[str, Any]
    ) -> Any:
        
        # Получаем информацию о пользователе и событии
        user_info = self._get_user_info(event)
        event_info = self._get_event_info(event)
        
        # Логируем входящее событие
        logger.info(f"📥 ВХОДЯЩЕЕ: {event_info} от {user_info}")
        
        # Засекаем время начала обработки
        start_time = datetime.now()
        
        try:
            # Выполняем handler
            result = await handler(event, data)
            
            # Вычисляем время обработки
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Логируем успешную обработку
            logger.info(f"✅ ОБРАБОТАНО: {event_info} за {processing_time:.3f}с")
            
            return result
            
        except Exception as e:
            # Вычисляем время до ошибки
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Логируем ошибку
            logger.error(f"❌ ОШИБКА: {event_info} за {processing_time:.3f}с - {str(e)}")
            
            # Пробрасываем ошибку дальше
            raise
    
    def _get_user_info(self, event: Union[Message, CallbackQuery, Update]) -> str:
        """Получить информацию о пользователе"""
        user = None
        
        # Если это Message объект
        if isinstance(event, Message):
            user = event.from_user
        # Если это CallbackQuery объект
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        # Если это Update объект
        elif isinstance(event, Update):
            if event.message:
                user = event.message.from_user
            elif event.callback_query:
                user = event.callback_query.from_user
            elif event.inline_query:
                user = event.inline_query.from_user
        
        if user:
            username = f"@{user.username}" if user.username else "без_username"
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            return f"👤 {full_name} ({username}, ID:{user.id})"
        
        return "👤 Неизвестный пользователь"
    
    def _get_event_info(self, event: Union[Message, CallbackQuery, Update]) -> str:
        """Получить информацию о событии"""
        
        # Если это Message объект
        if isinstance(event, Message):
            return self._format_message_info(event)
        
        # Если это CallbackQuery объект
        elif isinstance(event, CallbackQuery):
            data = event.data[:30] + "..." if len(event.data) > 30 else event.data
            return f"� Callback: '{data}'"
        
        # Если это Update объект
        elif isinstance(event, Update):
            if event.message:
                return self._format_message_info(event.message)
            elif event.callback_query:
                callback = event.callback_query
                data = callback.data[:30] + "..." if len(callback.data) > 30 else callback.data
                return f"🔘 Callback: '{data}'"
            elif event.inline_query:
                query = event.inline_query.query
                query_text = query[:30] + "..." if len(query) > 30 else query
                return f"🔍 Inline запрос: '{query_text}'"
        
        return "❓ Неизвестное событие"
    
    def _format_message_info(self, msg: Message) -> str:
        """Форматировать информацию о сообщении"""
        if msg.text:
            # Обрезаем длинные сообщения
            text = msg.text[:50] + "..." if len(msg.text) > 50 else msg.text
            return f"💬 Сообщение: '{text}'"
        elif msg.photo:
            return "📷 Фото"
        elif msg.document:
            return f"📄 Документ: {msg.document.file_name}"
        elif msg.voice:
            return "🎵 Голосовое сообщение"
        elif msg.location:
            return "📍 Геолокация"
        else:
            return "📝 Другое сообщение"


class DetailedLoggingMiddleware(LoggingMiddleware):
    """Расширенный middleware с более детальным логированием"""
    
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery, Update], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery, Update],
        data: Dict[str, Any]
    ) -> Any:
        
        # Базовое логирование
        result = await super().__call__(handler, event, data)
        
        # Дополнительное логирование для специальных случаев
        await self._log_special_events(event)
        
        return result
    
    async def _log_special_events(self, event: Union[Message, CallbackQuery, Update]):
        """Логирование специальных событий"""
        
        # Получаем Message объект
        msg = None
        callback = None
        
        if isinstance(event, Message):
            msg = event
        elif isinstance(event, CallbackQuery):
            callback = event
        elif isinstance(event, Update):
            msg = event.message
            callback = event.callback_query
        
        # Логируем команды
        if msg and msg.text and msg.text.startswith('/'):
            command = msg.text.split()[0]
            logger.info(f"🤖 КОМАНДА: {command}")
        
        # Логируем админские действия
        if msg and msg.from_user and msg.text:
            if any(word in msg.text.lower() for word in ['admin', 'report', 'stats']):
                logger.info(f"👑 АДМИН ДЕЙСТВИЕ: {msg.text[:100]}")
        
        # Логируем callback от админов
        if callback and callback.data:
            if any(word in callback.data for word in ['admin', 'report', 'stats']):
                logger.info(f"👑 АДМИН CALLBACK: {callback.data}")
