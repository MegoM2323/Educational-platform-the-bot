"""
Сервис для синхронизации данных между Django и Supabase
"""
from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from .supabase_service import supabase_auth_service

User = get_user_model()


class SupabaseSyncService:
    """
    Сервис для синхронизации пользователей между Django и Supabase
    """
    
    def sync_user_to_supabase(self, django_user: User) -> Dict[str, Any]:
        """
        Синхронизация пользователя Django с Supabase
        
        Args:
            django_user: Пользователь Django
        
        Returns:
            Dict с результатом синхронизации
        """
        try:
            # Подготавливаем данные профиля
            profile_data = {
                'full_name': f"{django_user.first_name} {django_user.last_name}".strip(),
                'phone': django_user.phone or '',
                'avatar_url': django_user.avatar.url if django_user.avatar else ''
            }
            
            # Обновляем профиль в Supabase
            result = supabase_auth_service.update_user_profile(
                str(django_user.id), 
                profile_data
            )
            
            if result['success']:
                # Синхронизируем роли
                self._sync_user_roles(django_user)
                return {
                    'success': True,
                    'message': 'Пользователь синхронизирован с Supabase'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Ошибка синхронизации')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка синхронизации: {str(e)}'
            }
    
    def _sync_user_roles(self, django_user: User) -> bool:
        """
        Синхронизация ролей пользователя
        
        Args:
            django_user: Пользователь Django
        
        Returns:
            True если успешно, False иначе
        """
        try:
            # Удаляем старые роли
            supabase_auth_service.service_client.table("user_roles").delete().eq("user_id", str(django_user.id)).execute()
            
            # Добавляем новую роль
            return supabase_auth_service._create_user_role(str(django_user.id), django_user.role)
            
        except Exception as e:
            print(f"Ошибка синхронизации ролей: {e}")
            return False
    
    def create_django_user_from_supabase(self, supabase_user_data: Dict[str, Any]) -> Optional[User]:
        """
        Создание пользователя Django на основе данных из Supabase
        
        Args:
            supabase_user_data: Данные пользователя из Supabase
        
        Returns:
            Пользователь Django или None
        """
        try:
            # Проверяем, существует ли пользователь
            user_id = supabase_user_data.get('id')
            if not user_id:
                return None
            
            # Пытаемся найти существующего пользователя
            try:
                django_user = User.objects.get(id=user_id)
                return django_user
            except User.DoesNotExist:
                pass
            
            # Получаем профиль из Supabase
            profile = supabase_auth_service.get_user_profile(user_id)
            roles = supabase_auth_service.get_user_roles(user_id)
            
            if not profile:
                return None
            
            # Определяем роль (берем первую из списка)
            role = roles[0] if roles else 'student'
            
            # Создаем пользователя Django
            django_user = User.objects.create_user(
                id=user_id,
                username=supabase_user_data.get('email', ''),
                email=supabase_user_data.get('email', ''),
                first_name=profile.get('full_name', '').split(' ')[0] if profile.get('full_name') else '',
                last_name=' '.join(profile.get('full_name', '').split(' ')[1:]) if profile.get('full_name') and len(profile.get('full_name', '').split(' ')) > 1 else '',
                phone=profile.get('phone', ''),
                role=role,
                is_active=True
            )
            
            # Создаем соответствующий профиль
            self._create_user_profile(django_user, role)
            
            return django_user
            
        except Exception as e:
            print(f"Ошибка создания пользователя Django: {e}")
            return None
    
    def _create_user_profile(self, user: User, role: str) -> None:
        """
        Создание профиля пользователя в зависимости от роли
        
        Args:
            user: Пользователь Django
            role: Роль пользователя
        """
        try:
            if role == 'student':
                from .models import StudentProfile
                StudentProfile.objects.get_or_create(user=user)
            elif role == 'teacher':
                from .models import TeacherProfile
                TeacherProfile.objects.get_or_create(user=user)
            elif role == 'tutor':
                from .models import TutorProfile
                TutorProfile.objects.get_or_create(user=user)
            elif role == 'parent':
                from .models import ParentProfile
                ParentProfile.objects.get_or_create(user=user)
        except Exception as e:
            print(f"Ошибка создания профиля: {e}")
    
    def sync_all_users(self) -> Dict[str, Any]:
        """
        Синхронизация всех пользователей Django с Supabase
        
        Returns:
            Dict с результатом синхронизации
        """
        try:
            users = User.objects.all()
            synced_count = 0
            errors = []
            
            for user in users:
                result = self.sync_user_to_supabase(user)
                if result['success']:
                    synced_count += 1
                else:
                    errors.append(f"Пользователь {user.email}: {result.get('error', 'Неизвестная ошибка')}")
            
            return {
                'success': True,
                'synced_count': synced_count,
                'total_count': users.count(),
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка массовой синхронизации: {str(e)}'
            }


# Глобальный экземпляр сервиса синхронизации
supabase_sync_service = SupabaseSyncService()
