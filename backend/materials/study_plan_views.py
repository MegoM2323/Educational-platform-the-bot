"""
API endpoints для генерации учебных планов через AI
Endpoint POST /api/materials/study-plan/generate/
"""
import logging
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from materials.models import Subject, SubjectEnrollment, StudyPlanGeneration
from materials.services.study_plan_generator_service import StudyPlanGeneratorService
from materials.services.openrouter_service import OpenRouterError
from materials.services.latex_compiler import LaTeXCompilationError
from materials.tasks import generate_study_plan_async


logger = logging.getLogger(__name__)
User = get_user_model()


# CSRF-exempt SessionAuthentication для API
class CSRFExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


@api_view(['POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def generate_study_plan(request):
    """
    Генерация учебного плана через AI (OpenRouter API)

    POST /api/materials/study-plan/generate/

    Request Body:
    {
        "student_id": int,
        "subject_id": int,
        "grade": int,
        "topic": str,
        "subtopics": str,
        "goal": str,
        "task_counts": {"A": int, "B": int, "C": int},
        "constraints": str (optional),
        "reference_level": str (optional, default: "средний"),
        "examples_count": str (optional),
        "video_duration": str (optional, default: "10-25"),
        "video_language": str (optional, default: "русский")
    }

    Response (success):
    {
        "success": true,
        "generation_id": int,
        "status": "completed",
        "files": [
            {"type": "problem_set", "url": "/media/..."},
            {"type": "reference_guide", "url": "/media/..."},
            {"type": "video_list", "url": "/media/..."},
            {"type": "weekly_plan", "url": "/media/..."}
        ]
    }

    Response (error):
    {
        "success": false,
        "error": str
    }
    """
    # Валидация роли преподавателя
    if request.user.role != User.Role.TEACHER:
        return Response(
            {
                'success': False,
                'error': 'Доступ запрещен. Требуется роль преподавателя.'
            },
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        # Парсинг payload
        student_id = request.data.get('student_id')
        subject_id = request.data.get('subject_id')
        grade = request.data.get('grade')
        topic = request.data.get('topic')
        subtopics = request.data.get('subtopics')
        goal = request.data.get('goal')
        task_counts = request.data.get('task_counts')

        # Валидация обязательных полей
        if not all([student_id, subject_id, grade, topic, subtopics, goal, task_counts]):
            error_msg = (
                'Отсутствуют обязательные поля: student_id, subject_id, '
                'grade, topic, subtopics, goal, task_counts'
            )
            return Response(
                {
                    'success': False,
                    'error': error_msg
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Валидация типов
        try:
            student_id = int(student_id)
            subject_id = int(subject_id)
            grade = int(grade)
        except (ValueError, TypeError):
            return Response(
                {
                    'success': False,
                    'error': 'student_id, subject_id, grade должны быть числами'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Валидация task_counts
        if not isinstance(task_counts, dict):
            return Response(
                {
                    'success': False,
                    'error': 'task_counts должен быть объектом'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Валидация существования студента
        try:
            student = User.objects.get(id=student_id, role=User.Role.STUDENT)
        except User.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': f'Студент с ID {student_id} не найден'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Валидация существования предмета
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': f'Предмет с ID {subject_id} не найден'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Валидация enrollment (teacher-student-subject)
        enrollment_exists = SubjectEnrollment.objects.filter(
            teacher=request.user,
            student=student,
            subject=subject,
            is_active=True
        ).exists()

        if not enrollment_exists:
            return Response(
                {
                    'success': False,
                    'error': f'Студент {student.get_full_name()} не зачислен на предмет {subject.name} к вам'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Подготовка параметров для сервиса
        params = {
            'subject': subject.name,
            'grade': grade,
            'topic': topic,
            'subtopics': subtopics,
            'goal': goal,
            'task_counts': task_counts,
            'constraints': request.data.get('constraints', ''),
            'reference_level': request.data.get('reference_level', 'средний'),
            'examples_count': request.data.get('examples_count', 'стандартный'),
            'video_duration': request.data.get('video_duration', '10-25'),
            'video_language': request.data.get('video_language', 'русский')
        }

        # Создание записи StudyPlanGeneration (статус pending)
        logger.info(
            f"Инициирована асинхронная генерация учебного плана | "
            f"teacher={request.user.email} | "
            f"student={student.email} | "
            f"subject={subject.name}"
        )

        # Находим enrollment для валидации
        try:
            enrollment = SubjectEnrollment.objects.get(
                teacher=request.user,
                student=student,
                subject=subject,
                is_active=True
            )
        except SubjectEnrollment.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': f'Студент {student.get_full_name()} не зачислен на предмет {subject.name} к вам'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Создаём запись на генерацию
        generation = StudyPlanGeneration.objects.create(
            teacher=request.user,
            student=student,
            subject=subject,
            enrollment=enrollment,
            parameters=params,
            status=StudyPlanGeneration.Status.PENDING,
            progress_message='Ожидает обработки...'
        )

        # Запускаем асинхронную задачу Celery
        generate_study_plan_async.delay(generation.id)

        logger.info(
            f"Celery задача запущена | "
            f"generation_id={generation.id} | "
            f"teacher={request.user.email}"
        )

        # Возвращаем немедленный ответ с generation_id для polling
        return Response(
            {
                'success': True,
                'generation_id': generation.id,
                'status': generation.status,
                'progress_message': generation.progress_message
            },
            status=status.HTTP_200_OK
        )

    except ValidationError as e:
        logger.warning(
            f"Ошибка валидации при инициировании генерации учебного плана | "
            f"teacher={request.user.email} | "
            f"error={str(e)}"
        )
        return Response(
            {
                'success': False,
                'error': str(e)
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        logger.error(
            f"Непредвиденная ошибка при инициировании генерации учебного плана | "
            f"teacher={request.user.email} | "
            f"error={str(e)}",
            exc_info=True
        )
        return Response(
            {
                'success': False,
                'error': f'Внутренняя ошибка сервера: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def generation_status(request, generation_id):
    """
    Получение статуса генерации учебного плана

    GET /api/materials/study-plan/generation/{generation_id}/

    Response:
    {
        "success": true,
        "generation_id": int,
        "status": "pending" | "processing" | "completed" | "failed",
        "progress_message": str,
        "error_message": str (если failed),
        "files": [
            {"type": "problem_set", "url": "/media/..."},
            ...
        ],
        "created_at": str,
        "updated_at": str,
        "completed_at": str (если completed/failed)
    }
    """
    try:
        # Получение записи генерации
        generation = StudyPlanGeneration.objects.select_related(
            'teacher', 'student', 'subject'
        ).get(id=generation_id)

        # Проверка прав доступа (только teacher который создал генерацию)
        if request.user != generation.teacher:
            return Response(
                {
                    'success': False,
                    'error': 'Доступ запрещён. Вы не являетесь автором этой генерации.'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Формирование ответа с файлами (если есть)
        files = []
        if generation.status == StudyPlanGeneration.Status.COMPLETED:
            for generated_file in generation.generated_files.filter(
                status='compiled'
            ).order_by('file_type'):
                files.append({
                    'type': generated_file.file_type,
                    'url': generated_file.file.url if generated_file.file else None
                })

        response_data = {
            'success': True,
            'generation_id': generation.id,
            'status': generation.status,
            'progress_message': generation.progress_message,
            'files': files,
            'created_at': generation.created_at.isoformat(),
            'updated_at': generation.updated_at.isoformat()
        }

        # Добавляем ошибку если failed
        if generation.status == StudyPlanGeneration.Status.FAILED:
            response_data['error_message'] = generation.error_message

        # Добавляем completed_at если завершено
        if generation.completed_at:
            response_data['completed_at'] = generation.completed_at.isoformat()

        return Response(response_data, status=status.HTTP_200_OK)

    except StudyPlanGeneration.DoesNotExist:
        return Response(
            {
                'success': False,
                'error': f'Генерация с ID {generation_id} не найдена'
            },
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        logger.error(
            f"Ошибка при получении статуса генерации | "
            f"generation_id={generation_id} | "
            f"error={str(e)}",
            exc_info=True
        )
        return Response(
            {
                'success': False,
                'error': f'Внутренняя ошибка сервера: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
