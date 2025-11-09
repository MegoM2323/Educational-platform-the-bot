from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db import transaction
import logging

from .teacher_dashboard_service import TeacherDashboardService
from .models import Material, Subject, SubjectEnrollment, MaterialSubmission, MaterialProgress, StudyPlan
from .serializers import MaterialFeedbackSerializer, MaterialSubmissionSerializer, MaterialCreateSerializer, StudyPlanSerializer, StudyPlanCreateSerializer, StudyPlanListSerializer
from reports.models import Report

logger = logging.getLogger(__name__)

User = get_user_model()


# CSRF-exempt SessionAuthentication для API
class CSRFExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
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
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
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


@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def teacher_materials(request):
    """
    Получить материалы преподавателя или создать новый материал
    """
    logger.info(f"[teacher_materials] {request.method} from: {request.user.username}")
    
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    if request.method == 'GET':
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
            logger.info(f"[teacher_materials] Returning {len(materials)} materials")
            return Response({'materials': materials}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'Ошибка при получении материалов: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    serializer = MaterialCreateSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        material = serializer.save()
        return Response({'id': material.id, 'title': material.title}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def distribute_material(request):
    """
    Распределить материал среди студентов
    """
    logger.info(f"[distribute_material] Request from: {request.user.username}")
    logger.info(f"[distribute_material] Request data: {request.data}")
    
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
        
        logger.info(f"[distribute_material] Result: {result}")
        
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
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def teacher_all_students(request):
    """
    Получить список ВСЕХ студентов для назначения предметов
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = TeacherDashboardService(request.user)
        students = service.get_all_students()
        
        return Response({'students': students}, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in teacher_all_students: {e}", exc_info=True)
        return Response(
            {'error': f'Ошибка при получении списка студентов: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
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
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
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
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
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
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
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


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def teacher_student_subjects(request, student_id: int):
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )

    enrollments = SubjectEnrollment.objects.filter(
        student_id=student_id,
        teacher=request.user,
        is_active=True
    ).select_related('subject', 'student')

    data = [
        {
            'enrollment_id': e.id,
            'student': {'id': e.student.id, 'name': e.student.get_full_name()},
            'subject': {'id': e.subject.id, 'name': e.get_subject_name(), 'color': e.subject.color},
            'enrolled_at': e.enrolled_at,
            'is_active': e.is_active,
        }
        for e in enrollments
    ]
    return Response({'subjects': data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def subject_students(request, subject_id: int):
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )

    enrollments = SubjectEnrollment.objects.filter(
        subject_id=subject_id,
        teacher=request.user,
        is_active=True
    ).select_related('student')

    students = [
        {
            'id': e.student.id,
            'name': e.student.get_full_name(),
            'email': e.student.email,
            'enrollment_id': e.id,
            'enrolled_at': e.enrolled_at,
        }
        for e in enrollments
    ]
    return Response({'students': students}, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def pending_submissions(request):
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )

    submissions = MaterialSubmission.objects.filter(
        material__author=request.user,
        status=MaterialSubmission.Status.SUBMITTED
    ).select_related('material', 'student')

    serializer = MaterialSubmissionSerializer(submissions, many=True, context={'request': request})
    return Response({'pending': serializer.data}, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def submission_feedback(request, submission_id: int):
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )

    submission = get_object_or_404(MaterialSubmission, id=submission_id)
    if submission.material.author_id != request.user.id:
        return Response(
            {'error': 'Вы не являетесь автором материала этого ответа'},
            status=status.HTTP_403_FORBIDDEN
        )
    if hasattr(submission, 'feedback'):
        return Response({'error': 'Фидбэк уже существует'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = MaterialFeedbackSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save(submission=submission)
        submission.status = MaterialSubmission.Status.REVIEWED
        submission.save(update_fields=['status'])
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def update_submission_status(request, submission_id: int):
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )

    submission = get_object_or_404(MaterialSubmission, id=submission_id)
    if submission.material.author_id != request.user.id:
        return Response(
            {'error': 'Вы не являетесь автором материала этого ответа'},
            status=status.HTTP_403_FORBIDDEN
        )

    new_status = request.data.get('status')
    valid_statuses = [s for s, _ in MaterialSubmission.Status.choices]
    if new_status not in valid_statuses:
        return Response({'error': f'Недопустимый статус. Допустимые: {valid_statuses}'}, status=status.HTTP_400_BAD_REQUEST)

    submission.status = new_status
    submission.save(update_fields=['status'])
    return Response({'id': submission.id, 'status': submission.status}, status=status.HTTP_200_OK)


@api_view(['GET', 'PUT'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def material_assignments(request, material_id: int):
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )

    material = get_object_or_404(Material, id=material_id)
    if material.author_id != request.user.id:
        return Response(
            {'error': 'Вы не являетесь автором этого материала'},
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method == 'GET':
        assigned = material.assigned_to.all()
        data = [{'id': s.id, 'name': s.get_full_name(), 'email': s.email} for s in assigned]
        return Response({'assigned_students': data}, status=status.HTTP_200_OK)

    student_ids = request.data.get('student_ids', [])
    if not isinstance(student_ids, list):
        return Response({'error': 'student_ids должен быть списком'}, status=status.HTTP_400_BAD_REQUEST)

    from django.contrib.auth import get_user_model
    UserModel = get_user_model()
    # Исключаем админов из списка при назначении материала
    students = UserModel.objects.filter(
        id__in=student_ids,
        role=UserModel.Role.STUDENT,
        is_staff=False,
        is_superuser=False
    )
    material.assigned_to.set(students)

    for s in students:
        MaterialProgress.objects.get_or_create(student=s, material=material)

    return Response({'assigned_count': students.count()}, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def get_all_subjects(request):
    """
    Получить все предметы
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = TeacherDashboardService(request.user)
        subjects = service.get_all_subjects()
        
        return Response({'subjects': subjects}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении предметов: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def get_all_students(request):
    """
    Получить всех студентов для назначения предметов
    Исключаем админов (is_staff и is_superuser)
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Получаем только активных студентов, исключая админов
        students = User.objects.filter(
            role=User.Role.STUDENT,
            is_active=True,
            is_staff=False,
            is_superuser=False
        ).select_related('student_profile').order_by('username')
        
        data = []
        for student in students:
            try:
                profile = student.student_profile
                profile_data = {
                    'grade': profile.grade,
                    'goal': profile.goal,
                    'progress_percentage': profile.progress_percentage
                }
            except:
                profile_data = {
                    'grade': 'Не указан',
                    'goal': '',
                    'progress_percentage': 0
                }
            
            data.append({
                'id': student.id,
                'name': student.get_full_name(),
                'email': student.email,
                'role': student.role,  # Добавляем роль для фильтрации на фронтенде
                'profile': profile_data
            })
        
        return Response({'students': data}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении студентов: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def teacher_study_plans(request):
    """
    Получить список планов занятий преподавателя или создать новый план
    GET: получить список всех планов преподавателя
    POST: создать новый план занятий
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        if request.method == 'GET':
            # Получить список планов
            student_id = request.query_params.get('student_id')
            subject_id = request.query_params.get('subject_id')
            status_filter = request.query_params.get('status')
            
            plans = StudyPlan.objects.filter(teacher=request.user)
            
            if student_id:
                try:
                    plans = plans.filter(student_id=int(student_id))
                except ValueError:
                    return Response(
                        {'error': 'student_id должен быть числом'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            if subject_id:
                try:
                    plans = plans.filter(subject_id=int(subject_id))
                except ValueError:
                    return Response(
                        {'error': 'subject_id должен быть числом'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            if status_filter:
                plans = plans.filter(status=status_filter)
            
            plans = plans.select_related('student', 'subject', 'teacher').order_by('-week_start_date', '-created_at')
            serializer = StudyPlanListSerializer(plans, many=True)
            
            return Response({'study_plans': serializer.data}, status=status.HTTP_200_OK)
        
        elif request.method == 'POST':
            # Создать новый план
            serializer = StudyPlanCreateSerializer(data=request.data, context={'request': request})
            
            if serializer.is_valid():
                plan = serializer.save()
                logger.info(
                    "Study plan created | teacher=%s | student=%s | subject=%s | status=%s",
                    request.user.id,
                    plan.student_id,
                    plan.subject_id,
                    plan.status
                )
                response_serializer = StudyPlanSerializer(plan)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
            logger.warning(
                "Study plan creation failed | teacher=%s | errors=%s",
                request.user.id,
                serializer.errors
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Error in teacher_study_plans: {e}", exc_info=True)
        return Response(
            {'error': f'Ошибка при работе с планами занятий: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'PATCH', 'DELETE'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def teacher_study_plan_detail(request, plan_id):
    """
    Получить, обновить или удалить план занятий
    GET: получить детали плана
    PATCH: обновить план (включая отправку - изменение статуса на 'sent')
    DELETE: удалить план
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        plan = get_object_or_404(StudyPlan, id=plan_id, teacher=request.user)
        
        if request.method == 'GET':
            serializer = StudyPlanSerializer(plan)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        elif request.method == 'PATCH':
            serializer = StudyPlanSerializer(plan, data=request.data, partial=True, context={'request': request})
            
            if serializer.is_valid():
                # Если статус меняется на 'sent', устанавливаем sent_at
                if 'status' in request.data and request.data['status'] == StudyPlan.Status.SENT:
                    from django.utils import timezone
                    if not plan.sent_at:
                        serializer.validated_data['sent_at'] = timezone.now()
                
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == 'DELETE':
            plan.delete()
            return Response({'message': 'План занятий удален'}, status=status.HTTP_204_NO_CONTENT)
    
    except Exception as e:
        logger.error(f"Error in teacher_study_plan_detail: {e}", exc_info=True)
        return Response(
            {'error': f'Ошибка при работе с планом занятий: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def send_study_plan(request, plan_id):
    """
    Отправить план занятий студенту (изменить статус на 'sent')
    """
    if request.user.role != User.Role.TEACHER:
        return Response(
            {'error': 'Доступ запрещен. Требуется роль преподавателя.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        plan = get_object_or_404(StudyPlan, id=plan_id, teacher=request.user)
        
        if plan.status == StudyPlan.Status.SENT:
            return Response(
                {'error': 'План уже отправлен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        plan.status = StudyPlan.Status.SENT
        plan.sent_at = timezone.now()
        plan.save()
        
        serializer = StudyPlanSerializer(plan)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error in send_study_plan: {e}", exc_info=True)
        return Response(
            {'error': f'Ошибка при отправке плана: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
