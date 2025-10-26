"""
Mock Supabase сервис для работы без подключения к Supabase
"""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class MockSupabaseAuthService:
    """
    Mock сервис для аутентификации без Supabase
    """
    
    def __init__(self):
        logger.info("Используется Mock Supabase сервис")
    
    def sign_up(self, email: str, password: str, user_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock регистрация"""
        logger.warning("Supabase не настроен - mock регистрация")
        return {
            "success": False,
            "error": "Supabase не настроен. Используйте стандартную регистрацию Django."
        }
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Mock вход"""
        logger.warning("Supabase не настроен - mock вход")
        return {
            "success": False,
            "error": "Supabase не настроен. Используйте стандартную аутентификацию Django."
        }
    
    def sign_out(self) -> Dict[str, Any]:
        """Mock выход"""
        logger.warning("Supabase не настроен - mock выход")
        return {
            "success": False,
            "error": "Supabase не настроен"
        }
    
    def get_user(self) -> Optional[Dict[str, Any]]:
        """Mock получение пользователя"""
        logger.warning("Supabase не настроен - mock получение пользователя")
        return None
    
    def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock обновление профиля"""
        logger.warning("Supabase не настроен - mock обновление профиля")
        return {
            "success": False,
            "error": "Supabase не настроен"
        }
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Mock получение профиля"""
        logger.warning("Supabase не настроен - mock получение профиля")
        return None
    
    def get_user_roles(self, user_id: str) -> list:
        """Mock получение ролей"""
        logger.warning("Supabase не настроен - mock получение ролей")
        return []
