from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db import transaction
import logging

from .teacher_dashboard_service import TeacherDashboardService
from .models import Material, Subject
from reports.models import Report

logger = logging.getLogger(__name__)

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_dashboard(request):
    """
    Получить данные дашборда преподавателя
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = TeacherDashboardService(request.user)
        dashboard_data = service.get_dashboard_data()
        
        return Response(dashboard_data, status=status.HTTP_200_OK)
        
    except ValueError as e:
        logger.error(f"Validation error in teacher dashboard: {e}")
        return Response(
            {'error': f'Ошибка валидации: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Unexpected error in teacher dashboard: {e}", exc_info=True)
        return Response(
            {'error': 'Внутренняя ошибка сервера при загрузке дашборда'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_students(request):
    """
    Получить список студентов преподавателя
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = TeacherDashboardService(request.user)
        students = service.get_teacher_students()
        
        return Response({'students': students}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении списка студентов: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_materials(request):
    """
    Получить материалы преподавателя
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = TeacherDashboardService(request.user)
        subject_id = request.GET.get('subject_id')
        if subject_id:
            try:
                subject_id = int(subject_id)
            except ValueError:
                return Response(
                    {'error': 'Неверный формат subject_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        materials = service.get_teacher_materials(subject_id)
        
        return Response({'materials': materials}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении материалов: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def distribute_material(request):
    """
    Распределить материал среди студентов
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        material_id = request.data.get('material_id')
        student_ids = request.data.get('student_ids', [])
        
        if not material_id:
            return Response(
                {'error': 'Не указан ID материала'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not student_ids:
            return Response(
                {'error': 'Не указаны ID студентов'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not isinstance(student_ids, list):
            return Response(
                {'error': 'student_ids должен быть списком'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = TeacherDashboardService(request.user)
        result = service.distribute_material(material_id, student_ids)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response(
            {'error': f'Ошибка при распределении материала: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_progress_overview(request):
    """
    Получить обзор прогресса студентов
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = TeacherDashboardService(request.user)
        student_id = request.GET.get('student_id')
        
        if student_id:
            try:
                student_id = int(student_id)
            except ValueError:
                return Response(
                    {'error': 'Неверный формат student_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        progress_data = service.get_student_progress_overview(student_id)
        
        return Response(progress_data, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response(
            {'error': 'Студент не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении обзора прогресса: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_student_report(request):
    """
    Создать отчет о студенте
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        student_id = request.data.get('student_id')
        if not student_id:
            return Response(
                {'error': 'Не указан ID студента'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, что студент существует
        student = get_object_or_404(User, id=student_id, role=User.Role.STUDENT)
        
        # Подготавливаем данные отчета
        report_data = {
            'title': request.data.get('title', f'Отчет по студенту {student.get_full_name()}'),
            'description': request.data.get('description', ''),
            'type': request.data.get('type', Report.Type.STUDENT_PROGRESS),
            'start_date': request.data.get('start_date'),
            'end_date': request.data.get('end_date'),
            'content': request.data.get('content', {})
        }
        
        # Валидация типа отчета
        valid_types = [choice[0] for choice in Report.Type.choices]
        if report_data['type'] not in valid_types:
            return Response(
                {'error': f'Неверный тип отчета. Доступные типы: {valid_types}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = TeacherDashboardService(request.user)
        result = service.create_student_report(student_id, report_data)
        
        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response(
            {'error': f'Ошибка при создании отчета: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_reports(request):
    """
    Получить отчеты преподавателя
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = TeacherDashboardService(request.user)
        reports = service.get_teacher_reports()
        
        return Response({'reports': reports}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении отчетов: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_general_chat(request):
    """
    Получить доступ к общему чату
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = TeacherDashboardService(request.user)
        chat_data = service.get_general_chat_access()
        
        if chat_data:
            return Response(chat_data, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Не удалось получить доступ к общему чату'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении доступа к чату: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
