from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import logging

from .parent_dashboard_service import ParentDashboardService
from .serializers import ParentDashboardSerializer, ChildSubjectsSerializer, PaymentInitiationSerializer
from accounts.staff_views import CSRFExemptSessionAuthentication

logger = logging.getLogger(__name__)

User = get_user_model()


class ParentDashboardView(generics.RetrieveAPIView):
    """
    API endpoint для получения данных дашборда родителя
    """
    authentication_classes = [TokenAuthentication, CSRFExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """
        Получить данные дашборда родителя
        """
        try:
            # Логируем информацию о пользователе и токене
            auth_header = request.META.get('HTTP_AUTHORIZATION', 'NOT SET')
            logger.info(f"[ParentDashboardView.get] Authorization header: {auth_header}")
            
            # Проверяем, какой токен используется
            if auth_header.startswith('Token '):
                token_key = auth_header.replace('Token ', '')
                from rest_framework.authtoken.models import Token
                try:
                    token_obj = Token.objects.get(key=token_key)
                    logger.info(f"[ParentDashboardView.get] Token belongs to user: {token_obj.user.username}, role: {token_obj.user.role}")
                    # Если токен принадлежит другому пользователю, чем request.user, это проблема
                    if token_obj.user.id != request.user.id:
                        logger.error(f"[ParentDashboardView.get] TOKEN MISMATCH! Token user: {token_obj.user.username} (id: {token_obj.user.id}), request.user: {request.user.username} (id: {request.user.id})")
                except Token.DoesNotExist:
                    logger.warning(f"[ParentDashboardView.get] Token not found in database")
            
            logger.info(f"[ParentDashboardView.get] Request from user: {request.user.username} (id: {request.user.id})")
            logger.info(f"[ParentDashboardView.get] User role: {request.user.role}, type: {type(request.user.role)}")
            logger.info(f"[ParentDashboardView.get] User authenticated: {request.user.is_authenticated}")
            logger.info(f"[ParentDashboardView.get] User.Role.PARENT: {User.Role.PARENT}")
            logger.info(f"[ParentDashboardView.get] Role match: {request.user.role == User.Role.PARENT}")
            
            if not request.user or not request.user.is_authenticated:
                return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Проверяем связь родитель-ребенок
            service = ParentDashboardService(request.user)
            dashboard_data = service.get_dashboard_data()
            logger.info(f"[ParentDashboardView.get] Dashboard data children count: {len(dashboard_data.get('children', []))}")
            logger.info(f"[ParentDashboardView.get] Dashboard data keys: {list(dashboard_data.keys())}")
            logger.info(f"[ParentDashboardView.get] Children data: {dashboard_data.get('children', [])}")
            
            # Логируем полный ответ для отладки
            import json
            logger.info(f"[ParentDashboardView.get] Full dashboard data (first 2000 chars): {json.dumps(dashboard_data, default=str, ensure_ascii=False)[:2000]}")
            
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
    authentication_classes = [TokenAuthentication, CSRFExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        try:
            service = ParentDashboardService(self.request.user)
            return service.get_children()
        except ValueError:
            return User.objects.none()
    
    def list(self, request, *args, **kwargs):
        try:
            logger.info(f"[ParentChildrenView.list] Request from user: {request.user.username}, role: {request.user.role}")
            service = ParentDashboardService(request.user)
            children = service.get_children()
            logger.info(f"[ParentChildrenView.list] Found {children.count()} children for parent {request.user.username}")
            
            result = []
            for child in children:
                logger.debug(f"[ParentChildrenView.list] Processing child: {child.username}")
                # Основные поля профиля
                student_profile = getattr(child, 'student_profile', None)
                grade = getattr(student_profile, 'grade', '') if student_profile else ''
                goal = getattr(student_profile, 'goal', '') if student_profile else ''
                
                # Предметы и статусы платежей
                subjects = []
                payments_info = service.get_payment_status(child)
                payments_by_enrollment = {p['enrollment_id']: p for p in payments_info}
                for enrollment in service.get_child_subjects(child):
                    payment = payments_by_enrollment.get(enrollment.id, None)
                    subjects.append({
                        'id': enrollment.subject.id,
                        'enrollment_id': enrollment.id,  # Добавляем enrollment_id
                        'name': enrollment.get_subject_name(),
                        'teacher_name': enrollment.teacher.get_full_name(),
                        'teacher_id': enrollment.teacher.id,
                        'enrollment_status': 'active' if enrollment.is_active else 'inactive',
                        'payment_status': (payment['status'] if payment else 'no_payment'),
                        'next_payment_date': payment['due_date'] if payment else None,
                        'has_subscription': service._has_active_subscription(enrollment),
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
            
            logger.info(f"[ParentChildrenView.list] Returning {len(result)} children")
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            logger.error(f"[ParentChildrenView.list] ValueError: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[ParentChildrenView.list] Unexpected error: {e}", exc_info=True)
            return Response({'error': f'Ошибка получения списка детей: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def get_child_subjects(request, child_id):
    """
    Получить предметы конкретного ребенка
    """
    try:
        logger.info(f"[get_child_subjects] Request from user: {request.user.username}, role: {request.user.role}")
        logger.info(f"[get_child_subjects] Authorization header: {request.META.get('HTTP_AUTHORIZATION', 'NOT SET')}")
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
                    'name': enrollment.get_subject_name(),
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
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def get_child_progress(request, child_id):
    """
    Получить прогресс конкретного ребенка
    """
    try:
        logger.info(f"[get_child_progress] Request from user: {request.user.username}, role: {request.user.role}")
        logger.info(f"[get_child_progress] Authorization header: {request.META.get('HTTP_AUTHORIZATION', 'NOT SET')}")
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
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def get_child_teachers(request, child_id):
    """
    Получить преподавателей ребенка
    """
    try:
        logger.info(f"[get_child_teachers] Request from user: {request.user.username}, role: {request.user.role}")
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
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def parent_payments(request):
    """
    История платежей родителя
    """
    try:
        logger.info(f"[parent_payments] Request from user: {request.user.username}, role: {request.user.role}")
        logger.info(f"[parent_payments] Authorization header: {request.META.get('HTTP_AUTHORIZATION', 'NOT SET')}")
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
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
@transaction.atomic
def initiate_payment(request, child_id, enrollment_id):
    """
    Инициировать платеж за предмет с конкретным преподавателем
    Использует enrollment_id для точного указания предмета и преподавателя
    """
    try:
        logger.info(f"[initiate_payment] Request from user: {request.user.username}, role: {request.user.role}")
        logger.info(f"[initiate_payment] child_id: {child_id}, enrollment_id: {enrollment_id}")
        logger.info(f"[initiate_payment] Request data: {request.data}")
        
        service = ParentDashboardService(request.user)
        child = User.objects.get(id=child_id, role=User.Role.STUDENT)
        
        if child not in service.get_children():
            return Response(
                {'error': 'Ребенок не принадлежит данному родителю'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем зачисление (enrollment) по ID
        from .models import SubjectEnrollment
        try:
            enrollment = SubjectEnrollment.objects.get(
                id=enrollment_id,
                student=child,
                is_active=True
            )
        except SubjectEnrollment.DoesNotExist:
            return Response(
                {'error': 'Зачисление не найдено или неактивно'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Валидация данных
        serializer = PaymentInitiationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        amount = Decimal(str(serializer.validated_data['amount']))
        description = serializer.validated_data.get('description', '')
        create_subscription = serializer.validated_data.get('create_subscription', False)
        
        if amount <= 0:
            return Response(
                {'error': 'Сумма должна быть больше нуля'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment_data = service.initiate_payment(
            child=child,
            enrollment=enrollment,
            amount=amount,
            description=description,
            create_subscription=create_subscription,
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
        logger.error(f"Error initiating payment: {e}", exc_info=True)
        error_message = str(e)
        # Если это ошибка уникальности подписки, даём более понятное сообщение
        if 'UNIQUE constraint failed' in error_message and 'subscription' in error_message.lower():
            error_message = 'Подписка для этого предмета уже существует. Используйте кнопку "Отменить подписку" для отмены текущей подписки.'
        return Response(
            {'error': f'Ошибка при создании платежа: {error_message}'}, 
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


@api_view(['POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
@transaction.atomic
def cancel_subscription(request, child_id, enrollment_id):
    """
    Отменить подписку на регулярные платежи
    """
    try:
        service = ParentDashboardService(request.user)
        child = User.objects.get(id=child_id, role=User.Role.STUDENT)
        
        if child not in service.get_children():
            return Response(
                {'error': 'Ребенок не принадлежит данному родителю'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем зачисление
        from .models import SubjectEnrollment, SubjectSubscription
        try:
            enrollment = SubjectEnrollment.objects.get(
                id=enrollment_id,
                student=child,
                is_active=True
            )
        except SubjectEnrollment.DoesNotExist:
            return Response(
                {'error': 'Зачисление не найдено или неактивно'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Проверяем наличие подписки
        try:
            subscription = SubjectSubscription.objects.get(
                enrollment=enrollment,
                status=SubjectSubscription.Status.ACTIVE
            )
        except SubjectSubscription.DoesNotExist:
            return Response(
                {'error': 'Активная подписка не найдена'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Отменяем подписку
        subscription.status = SubjectSubscription.Status.CANCELLED
        subscription.cancelled_at = timezone.now()
        subscription.save()
        
        # Если есть ID подписки в ЮКассу, можно отменить и там
        # (требует дополнительной интеграции с API ЮКассы)
        
        return Response({
            'success': True,
            'message': 'Подписка успешно отменена'
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response(
            {'error': 'Ребенок не найден'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}", exc_info=True)
        return Response(
            {'error': 'Ошибка при отмене подписки'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
