"""
Views for Teacher Progress Viewer (T403)
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.http import HttpResponse
from django.db.models import Count, Sum, Avg, Q
import logging
import csv
from io import StringIO

from .models import KnowledgeGraph, LessonProgress, ElementProgress, GraphLesson
from .teacher_progress_serializers import (
    StudentProgressOverviewSerializer,
    LessonProgressDetailSerializer,
    ElementProgressDetailSerializer
)
from .permissions import IsTeacherOrAdmin

logger = logging.getLogger(__name__)


class GraphProgressOverviewView(APIView):
    """
    GET /api/knowledge-graph/{graph_id}/progress/ - обзор прогресса всех студентов в графе
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get(self, request, graph_id):
        try:
            # Получить граф
            graph = KnowledgeGraph.objects.select_related('created_by', 'student', 'subject').get(id=graph_id)

            # Проверка прав (только создатель графа)
            if graph.created_by != request.user and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'Только создатель графа может просматривать прогресс'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Получить прогресс студента
            student = graph.student

            # Получить все уроки в графе
            graph_lessons = GraphLesson.objects.filter(graph=graph).select_related('lesson')
            total_lessons = graph_lessons.count()

            # Получить прогресс по урокам
            lesson_progress_list = LessonProgress.objects.filter(
                student=student,
                graph_lesson__graph=graph
            ).select_related('graph_lesson')

            completed_lessons = lesson_progress_list.filter(status='completed').count()

            # Рассчитать общий процент завершения
            if total_lessons > 0:
                completion_percentage = (completed_lessons / total_lessons) * 100
            else:
                completion_percentage = 0

            # Рассчитать общие баллы
            total_score = lesson_progress_list.aggregate(total=Sum('total_score'))['total'] or 0
            max_possible_score = lesson_progress_list.aggregate(total=Sum('max_possible_score'))['total'] or 0

            # Последняя активность
            last_activity = lesson_progress_list.order_by('-last_activity').first()
            last_activity_date = last_activity.last_activity if last_activity else None

            # Сформировать данные
            student_data = {
                'student_id': student.id,
                'student_name': student.get_full_name(),
                'student_email': student.email,
                'completion_percentage': round(completion_percentage, 2),
                'lessons_completed': completed_lessons,
                'lessons_total': total_lessons,
                'total_score': total_score,
                'max_possible_score': max_possible_score,
                'last_activity': last_activity_date,
            }

            serializer = StudentProgressOverviewSerializer(student_data)

            return Response({
                'success': True,
                'data': {
                    'graph_id': graph.id,
                    'subject_name': graph.subject.name,
                    'student': serializer.data
                }
            }, status=status.HTTP_200_OK)

        except KnowledgeGraph.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Граф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in GraphProgressOverviewView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при получении прогресса: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StudentDetailedProgressView(APIView):
    """
    GET /api/knowledge-graph/{graph_id}/students/{student_id}/progress/ - детальный прогресс студента
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get(self, request, graph_id, student_id):
        try:
            # Получить граф
            graph = KnowledgeGraph.objects.select_related('created_by', 'student').get(id=graph_id)

            # Проверка прав
            if graph.created_by != request.user and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'Только создатель графа может просматривать прогресс'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Проверка что student_id соответствует графу
            if graph.student.id != int(student_id):
                return Response(
                    {'success': False, 'error': 'Студент не принадлежит этому графу'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Получить все уроки в графе с прогрессом (FIX T019: устранение N+1 запросов)
            from django.db.models import Prefetch

            graph_lessons = GraphLesson.objects.filter(graph=graph).select_related('lesson').prefetch_related(
                'lesson__elements',
                Prefetch(
                    'progress',
                    queryset=LessonProgress.objects.filter(student=graph.student),
                    to_attr='student_progress_list'
                )
            )

            lessons_data = []
            for gl in graph_lessons:
                # Получить прогресс из prefetch (без дополнительных запросов)
                progress = gl.student_progress_list[0] if gl.student_progress_list else None

                if progress:
                    lesson_data = {
                        'lesson_id': gl.lesson.id,
                        'lesson_title': gl.lesson.title,
                        'status': progress.status,
                        'completion_percent': progress.completion_percent,
                        'completed_elements': progress.completed_elements,
                        'total_elements': progress.total_elements,
                        'total_score': progress.total_score,
                        'max_possible_score': progress.max_possible_score,
                        'started_at': progress.started_at,
                        'completed_at': progress.completed_at,
                        'total_time_spent_seconds': progress.total_time_spent_seconds,
                    }
                else:
                    lesson_data = {
                        'lesson_id': gl.lesson.id,
                        'lesson_title': gl.lesson.title,
                        'status': 'not_started',
                        'completion_percent': 0,
                        'completed_elements': 0,
                        'total_elements': gl.lesson.elements.count(),
                        'total_score': 0,
                        'max_possible_score': gl.lesson.total_max_score,
                        'started_at': None,
                        'completed_at': None,
                        'total_time_spent_seconds': 0,
                    }

                lessons_data.append(lesson_data)

            serializer = LessonProgressDetailSerializer(lessons_data, many=True)

            return Response({
                'success': True,
                'data': {
                    'student_id': graph.student.id,
                    'student_name': graph.student.get_full_name(),
                    'lessons': serializer.data
                }
            }, status=status.HTTP_200_OK)

        except KnowledgeGraph.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Граф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in StudentDetailedProgressView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при получении детального прогресса: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LessonDetailView(APIView):
    """
    GET /api/knowledge-graph/{graph_id}/students/{student_id}/lesson/{lesson_id}/ - детали урока с ответами
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get(self, request, graph_id, student_id, lesson_id):
        try:
            # Получить граф
            graph = KnowledgeGraph.objects.select_related('created_by', 'student').get(id=graph_id)

            # Проверка прав
            if graph.created_by != request.user and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'Только создатель графа может просматривать прогресс'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Проверка что student_id соответствует графу
            if graph.student.id != int(student_id):
                return Response(
                    {'success': False, 'error': 'Студент не принадлежит этому графу'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Получить GraphLesson
            graph_lesson = GraphLesson.objects.filter(
                graph=graph,
                lesson_id=lesson_id
            ).select_related('lesson').first()

            if not graph_lesson:
                return Response(
                    {'success': False, 'error': 'Урок не найден в графе'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Получить все элементы урока с прогрессом (FIX T019: устранение N+1 запросов)
            from .models import LessonElement
            from django.db.models import Prefetch

            lesson_elements = LessonElement.objects.filter(
                lesson=graph_lesson.lesson
            ).select_related('element').prefetch_related(
                Prefetch(
                    'element__student_progress',
                    queryset=ElementProgress.objects.filter(
                        student=graph.student,
                        graph_lesson=graph_lesson
                    ),
                    to_attr='student_progress_list'
                )
            ).order_by('order')

            elements_data = []
            for le in lesson_elements:
                # Получить прогресс из prefetch (без дополнительных запросов)
                progress = le.element.student_progress_list[0] if le.element.student_progress_list else None

                element_data = {
                    'element_id': le.element.id,
                    'element_type': le.element.element_type,
                    'element_title': le.element.title,
                    'student_answer': progress.answer if progress else None,
                    'score': progress.score if progress else None,
                    'max_score': le.element.max_score,
                    'status': progress.status if progress else 'not_started',
                    'completed_at': progress.completed_at if progress else None,
                    'attempts': progress.attempts if progress else 0,
                }

                # Добавить правильный ответ для quick_question
                if le.element.element_type == 'quick_question':
                    element_data['correct_answer'] = le.element.content.get('correct_answer')
                    element_data['choices'] = le.element.content.get('choices')

                elements_data.append(element_data)

            serializer = ElementProgressDetailSerializer(elements_data, many=True)

            return Response({
                'success': True,
                'data': {
                    'lesson_id': graph_lesson.lesson.id,
                    'lesson_title': graph_lesson.lesson.title,
                    'elements': serializer.data
                }
            }, status=status.HTTP_200_OK)

        except KnowledgeGraph.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Граф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in LessonDetailView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при получении деталей урока: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExportProgressView(APIView):
    """
    GET /api/knowledge-graph/{graph_id}/export/?format=csv - экспорт прогресса в CSV
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get(self, request, graph_id):
        try:
            # Получить граф
            graph = KnowledgeGraph.objects.select_related('created_by', 'student', 'subject').get(id=graph_id)

            # Проверка прав
            if graph.created_by != request.user and not request.user.is_staff:
                return Response(
                    {'success': False, 'error': 'Только создатель графа может экспортировать прогресс'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Проверка формата
            export_format = request.query_params.get('format', 'csv')
            if export_format != 'csv':
                return Response(
                    {'success': False, 'error': 'Поддерживается только формат CSV'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Создать CSV
            output = StringIO()
            writer = csv.writer(output)

            # Заголовки
            writer.writerow([
                'Student Name',
                'Student Email',
                'Subject',
                'Lesson Title',
                'Status',
                'Completion %',
                'Score',
                'Max Score',
                'Started At',
                'Completed At',
                'Time Spent (minutes)'
            ])

            # Получить все уроки и прогресс
            graph_lessons = GraphLesson.objects.filter(graph=graph).select_related('lesson')

            for gl in graph_lessons:
                progress = LessonProgress.objects.filter(
                    student=graph.student,
                    graph_lesson=gl
                ).first()

                if progress:
                    writer.writerow([
                        graph.student.get_full_name(),
                        graph.student.email,
                        graph.subject.name,
                        gl.lesson.title,
                        progress.get_status_display(),
                        f"{progress.completion_percent}%",
                        progress.total_score,
                        progress.max_possible_score,
                        progress.started_at.strftime('%Y-%m-%d %H:%M') if progress.started_at else '',
                        progress.completed_at.strftime('%Y-%m-%d %H:%M') if progress.completed_at else '',
                        round(progress.total_time_spent_seconds / 60, 2) if progress.total_time_spent_seconds else 0
                    ])
                else:
                    writer.writerow([
                        graph.student.get_full_name(),
                        graph.student.email,
                        graph.subject.name,
                        gl.lesson.title,
                        'Not Started',
                        '0%',
                        0,
                        gl.lesson.total_max_score,
                        '',
                        '',
                        0
                    ])

            # Вернуть CSV файл
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="progress_graph_{graph_id}.csv"'

            return response

        except KnowledgeGraph.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Граф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in ExportProgressView: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': f'Ошибка при экспорте: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
