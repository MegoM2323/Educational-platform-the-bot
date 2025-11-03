from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal
import logging

from .parent_dashboard_service import ParentDashboardService
from .serializers import ParentDashboardSerializer, ChildSubjectsSerializer, PaymentInitiationSerializer

logger = logging.getLogger(__name__)

User = get_user_model()


class ParentDashboardView(generics.RetrieveAPIView):
    """
    API endpoint для получения данных дашборда родителя
    """
    # Разрешаем доступ всем, статус 401 вернем вручную, чтобы соответствовать ожиданиям тестов
    permission_classes = [AllowAny]
    
    def get(self, request, *args, **kwargs):
        """
        Получить данные дашборда родителя
        """
        try:
            if not request.user or not request.user.is_authenticated:
                return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
            # Проверяем связь родитель-ребенок
            service = ParentDashboardService(request.user)
            dashboard_data = service.get_dashboard_data()
            return Response(dashboard_data, status=status.HTTP_200_OK)
        except ValueError as e:
            logger.error(f"Validation error in parent dashboard: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error in parent dashboard: {e}", exc_info=True)
            return Response(
                {'error': 'Внутренняя ошибка сервера при загрузке дашборда'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ParentChildrenView(generics.ListAPIView):
    """
    API endpoint для получения списка детей родителя
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        try:
            service = ParentDashboardService(self.request.user)
            return service.get_children()
        except ValueError:
            return User.objects.none()
    
    def list(self, request, *args, **kwargs):
        try:
            service = ParentDashboardService(request.user)
            children = service.get_children()
            
            result = []
            for child in children:
                # Основные поля профиля
                student_profile = getattr(child, 'student_profile', None)
                grade = getattr(student_profile, 'grade', '') if student_profile else ''
                goal = getattr(student_profile, 'goal', '') if student_profile else ''
                
                # Предметы и статусы платежей
                subjects = []
                payments = {p['subject']: p for p in service.get_payment_status(child)}
                for enrollment in service.get_child_subjects(child):
                    subj_name = enrollment.subject.name
                    pay = payments.get(subj_name)
                    subjects.append({
                        'id': enrollment.subject.id,
                        'name': subj_name,
                        'teacher_name': enrollment.teacher.get_full_name(),
                        'enrollment_status': 'active' if enrollment.is_active else 'inactive',
                        'payment_status': (pay['status'] if pay else 'no_payment'),
                    })
                
                # Совместимость: возвращаем как 'name' (ожидается тестами) и 'full_name'
                result.append({
                    'id': child.id,
                    'name': child.get_full_name(),
                    'full_name': child.get_full_name(),
                    'email': child.email,
                    'grade': str(grade) if grade is not None else '',
                    'goal': goal or '',
                    'subjects': subjects,
                })
            
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_child_subjects(request, child_id):
    """
    Получить предметы конкретного ребенка
    """
    try:
        service = ParentDashboardService(request.user)
        child = User.objects.get(id=child_id, role=User.Role.STUDENT)
        
        if child not in service.get_children():
            return Response(
                {'error': 'Ребенок не принадлежит данному родителю'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        subjects = service.get_child_subjects(child)
        subjects_data = []
        
        for enrollment in subjects:
            subject_data = {
                'enrollment_id': enrollment.id,
                'subject': {
                    'id': enrollment.subject.id,
                    'name': enrollment.subject.name,
                    'color': enrollment.subject.color,
                    'description': enrollment.subject.description
                },
                'teacher': {
                    'id': enrollment.teacher.id,
                    'name': enrollment.teacher.get_full_name(),
                    'email': enrollment.teacher.email
                },
                'enrolled_at': enrollment.enrolled_at,
                'is_active': enrollment.is_active
            }
            subjects_data.append(subject_data)
        
        return Response(subjects_data, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response(
            {'error': 'Ребенок не найден'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_child_progress(request, child_id):
    """
    Получить прогресс конкретного ребенка
    """
    try:
        service = ParentDashboardService(request.user)
        child = User.objects.get(id=child_id, role=User.Role.STUDENT)
        
        if child not in service.get_children():
            return Response(
                {'error': 'Ребенок не принадлежит данному родителю'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        progress_data = service.get_child_progress(child)
        return Response(progress_data, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response(
            {'error': 'Ребенок не найден'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_child_teachers(request, child_id):
    """
    Получить преподавателей ребенка
    """
    try:
        service = ParentDashboardService(request.user)
        child = User.objects.get(id=child_id, role=User.Role.STUDENT)
        
        if child not in service.get_children():
            return Response(
                {'error': 'Ребенок не принадлежит данному родителю'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        teachers = service.get_child_teachers(child)
        return Response(teachers, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response(
            {'error': 'Ребенок не найден'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def parent_payments(request):
    """
    История платежей родителя
    """
    try:
        service = ParentDashboardService(request.user)
        data = service.get_parent_payments()
        return Response(data, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def parent_pending_payments(request):
    """
    Ожидающие платежи родителя
    """
    try:
        service = ParentDashboardService(request.user)
        data = service.get_parent_pending_payments()
        return Response(data, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_status(request, child_id):
    """
    Получить статус платежей для ребенка
    """
    try:
        service = ParentDashboardService(request.user)
        child = User.objects.get(id=child_id, role=User.Role.STUDENT)
        
        if child not in service.get_children():
            return Response(
                {'error': 'Ребенок не принадлежит данному родителю'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        payment_data = service.get_payment_status(child)
        return Response(payment_data, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response(
            {'error': 'Ребенок не найден'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def initiate_payment(request, child_id, subject_id):
    """
    Инициировать платеж за предмет
    """
    try:
        service = ParentDashboardService(request.user)
        child = User.objects.get(id=child_id, role=User.Role.STUDENT)
        
        if child not in service.get_children():
            return Response(
                {'error': 'Ребенок не принадлежит данному родителю'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Валидация данных
        serializer = PaymentInitiationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        amount = Decimal(str(serializer.validated_data['amount']))
        description = serializer.validated_data.get('description', '')
        
        if amount <= 0:
            return Response(
                {'error': 'Сумма должна быть больше нуля'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment_data = service.initiate_payment(
            child=child,
            subject_id=subject_id,
            amount=amount,
            description=description,
            request=request
        )
        # В API возвращаем сумму как строку с двумя знаками после запятой
        payment_data_api = dict(payment_data)
        payment_data_api['amount'] = f"{payment_data['amount']:.2f}"
        
        return Response(payment_data_api, status=status.HTTP_201_CREATED)
    except User.DoesNotExist:
        return Response(
            {'error': 'Ребенок не найден'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': 'Ошибка при создании платежа'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_reports(request, child_id=None):
    """
    Получить отчеты о прогрессе (пока заглушка)
    """
    try:
        service = ParentDashboardService(request.user)
        
        if child_id:
            child = User.objects.get(id=child_id, role=User.Role.STUDENT)
            if child not in service.get_children():
                return Response(
                    {'error': 'Ребенок не принадлежит данному родителю'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            reports = service.get_reports(child)
        else:
            reports = service.get_reports()
        
        # Пока возвращаем пустой список, так как модель отчетов еще не создана
        return Response([], status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response(
            {'error': 'Ребенок не найден'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
