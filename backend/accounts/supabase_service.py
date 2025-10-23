"""
Сервис для работы с Supabase аутентификацией
"""
import os
from typing import Optional, Dict, Any
from django.conf import settings
from supabase import create_client, Client
from supabase._sync.client import SyncClient


class SupabaseAuthService:
    """
    Сервис для работы с аутентификацией через Supabase
    """
    
    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_KEY
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL и SUPABASE_KEY должны быть установлены в настройках")
        
        # Клиент для обычных операций (с ограниченными правами)
        self.client: Client = create_client(self.url, self.key)
        
        # Клиент с правами сервиса (для административных операций)
        if self.service_key:
            self.service_client: Client = create_client(self.url, self.service_key)
        else:
            self.service_client = self.client
    
    def sign_up(self, email: str, password: str, user_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Регистрация нового пользователя
        
        Args:
            email: Email пользователя
            password: Пароль
            user_data: Дополнительные данные пользователя (имя, роль и т.д.)
        
        Returns:
            Dict с информацией о пользователе
        """
        try:
            # Создаем пользователя напрямую через Admin API
            import requests
            
            # Подготовка данных для создания пользователя
            create_user_data = {
                "email": email,
                "password": password,
                "email_confirm": True,  # Подтверждаем email автоматически
                "user_metadata": user_data or {}
            }
            
            # Создаем пользователя через Admin API
            admin_url = f"{self.url}/auth/v1/admin/users"
            headers = {
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(admin_url, json=create_user_data, headers=headers)
            
            if response.status_code == 200:
                user_info = response.json()
                
                # Создаем профиль пользователя
                if user_data and 'role' in user_data:
                    self._create_user_role(user_info['id'], user_data['role'])
                
                return {
                    "success": True,
                    "user": {
                        "id": user_info['id'],
                        "email": user_info['email'],
                        "created_at": user_info['created_at'],
                    }
                }
            else:
                error_data = response.json() if response.content else {}
                return {
                    "success": False,
                    "error": error_data.get('msg', f"Ошибка создания пользователя: {response.status_code}")
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        Вход пользователя
        
        Args:
            email: Email пользователя
            password: Пароль
        
        Returns:
            Dict с информацией о сессии
        """
        try:
            response = self.service_client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                return {
                    "success": True,
                    "user": {
                        "id": response.user.id,
                        "email": response.user.email,
                    },
                    "session": response.session
                }
            else:
                return {
                    "success": False,
                    "error": "Неверные учетные данные"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def sign_out(self) -> Dict[str, Any]:
        """
        Выход пользователя
        
        Returns:
            Dict с результатом операции
        """
        try:
            self.client.auth.sign_out()
            return {
                "success": True,
                "message": "Выход выполнен успешно"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user(self) -> Optional[Dict[str, Any]]:
        """
        Получение текущего пользователя
        
        Returns:
            Dict с информацией о пользователе или None
        """
        try:
            user = self.client.auth.get_user()
            if user:
                return {
                    "id": user.id,
                    "email": user.email,
                    "created_at": user.created_at,
                }
            return None
        except Exception as e:
            return None
    
    def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновление профиля пользователя
        
        Args:
            user_id: ID пользователя
            profile_data: Данные для обновления
        
        Returns:
            Dict с результатом операции
        """
        try:
            # Обновляем профиль в таблице profiles
            response = self.service_client.table("profiles").update(profile_data).eq("id", user_id).execute()
            
            return {
                "success": True,
                "data": response.data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_user_role(self, user_id: str, role: str) -> bool:
        """
        Создание роли пользователя
        
        Args:
            user_id: ID пользователя
            role: Роль пользователя
        
        Returns:
            True если успешно, False иначе
        """
        try:
            self.service_client.table("user_roles").insert({
                "user_id": user_id,
                "role": role
            }).execute()
            return True
        except Exception as e:
            print(f"Ошибка при создании роли: {e}")
            return False
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение профиля пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Dict с профилем пользователя или None
        """
        try:
            response = self.service_client.table("profiles").select("*").eq("id", user_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Ошибка при получении профиля: {e}")
            return None
    
    def get_user_roles(self, user_id: str) -> list:
        """
        Получение ролей пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Список ролей пользователя
        """
        try:
            response = self.service_client.table("user_roles").select("role").eq("user_id", user_id).execute()
            return [item["role"] for item in response.data] if response.data else []
        except Exception as e:
            print(f"Ошибка при получении ролей: {e}")
            return []


# Глобальный экземпляр сервиса
supabase_auth_service = SupabaseAuthService()
