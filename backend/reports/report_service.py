from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from django.contrib.auth import get_user_model
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .models import StudentReport, Report, ReportRecipient, AnalyticsData
from materials.models import Material, MaterialProgress
from applications.telegram_service import TelegramService

User = get_user_model()


class ReportService:
    """
    Сервис для создания и управления отчетами
    Обеспечивает создание отчетов и автоматические уведомления родителей
    """
    
    def __init__(self, teacher: User):
        """
        Инициализация сервиса для конкретного преподавателя
        
        Args:
            teacher: Пользователь с ролью 'teacher'
        """
        if teacher.role != User.Role.TEACHER:
            raise ValueError("Пользователь должен иметь роль 'teacher'")
        
        self.teacher = teacher
        self.telegram_service = TelegramService()
    
    def create_student_report(self, student_id: int, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создать отчет о студенте
        
        Args:
            student_id: ID студента
            report_data: Данные отчета
            
        Returns:
            Результат создания отчета
        """
        try:
            student = User.objects.get(id=student_id, role=User.Role.STUDENT)
            
            # Создаем отчет
            report = StudentReport.objects.create(
                title=report_data.get('title', f'Отчет по студенту {student.get_full_name()}'),
                description=report_data.get('description', ''),
                report_type=report_data.get('report_type', StudentReport.ReportType.PROGRESS),
                teacher=self.teacher,
                student=student,
                period_start=report_data.get('period_start', timezone.now().date()),
                period_end=report_data.get('period_end', timezone.now().date()),
                content=report_data.get('content', {}),
                overall_grade=report_data.get('overall_grade', ''),
                progress_percentage=report_data.get('progress_percentage', 0),
                attendance_percentage=report_data.get('attendance_percentage', 0),
                behavior_rating=report_data.get('behavior_rating', 5),
                recommendations=report_data.get('recommendations', ''),
                concerns=report_data.get('concerns', ''),
                achievements=report_data.get('achievements', ''),
                status=StudentReport.Status.DRAFT
            )
            
            # Автоматически отправляем уведомление родителю
            if report.parent:
                self._send_parent_notification(report)
                report.status = StudentReport.Status.SENT
                report.sent_at = timezone.now()
                report.save()
            
            return {
                'success': True,
                'message': 'Отчет успешно создан',
                'report_id': report.id,
                'report_title': report.title,
                'sent_to_parent': bool(report.parent)
            }
            
        except User.DoesNotExist:
            return {
                'success': False,
                'message': 'Студент не найден'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Ошибка при создании отчета: {str(e)}'
            }
    
    def get_teacher_reports(self, student_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получить отчеты преподавателя
        
        Args:
            student_id: ID студента для фильтрации (опционально)
            
        Returns:
            Список отчетов преподавателя
        """
        reports_query = StudentReport.objects.filter(teacher=self.teacher)
        
        if student_id:
            reports_query = reports_query.filter(student_id=student_id)
        
        reports = reports_query.select_related('student', 'parent').order_by('-created_at')
        
        result = []
        for report in reports:
            result.append({
                'id': report.id,
                'title': report.title,
                'description': report.description,
                'report_type': report.report_type,
                'status': report.status,
                'student': {
                    'id': report.student.id,
                    'name': report.student.get_full_name(),
                    'email': report.student.email
                },
                'parent': {
                    'id': report.parent.id,
                    'name': report.parent.get_full_name(),
                    'email': report.parent.email
                } if report.parent else None,
                'period_start': report.period_start,
                'period_end': report.period_end,
                'overall_grade': report.overall_grade,
                'progress_percentage': report.progress_percentage,
                'attendance_percentage': report.attendance_percentage,
                'behavior_rating': report.behavior_rating,
                'recommendations': report.recommendations,
                'concerns': report.concerns,
                'achievements': report.achievements,
                'created_at': report.created_at,
                'sent_at': report.sent_at,
                'read_at': report.read_at
            })
        
        return result
    
    def get_student_reports_for_parent(self, parent_id: int) -> List[Dict[str, Any]]:
        """
        Получить отчеты о детях для родителя
        
        Args:
            parent_id: ID родителя
            
        Returns:
            Список отчетов о детях
        """
        try:
            parent = User.objects.get(id=parent_id, role=User.Role.PARENT)
            
            # Получаем всех детей родителя через профиль
            try:
                parent_profile = parent.parent_profile
                children = parent_profile.children.all()
            except:
                children = User.objects.none()
            
            # Получаем отчеты о детях
            reports = StudentReport.objects.filter(
                student__in=children
            ).select_related('student', 'teacher').order_by('-created_at')
            
            result = []
            for report in reports:
                result.append({
                    'id': report.id,
                    'title': report.title,
                    'description': report.description,
                    'report_type': report.report_type,
                    'status': report.status,
                    'student': {
                        'id': report.student.id,
                        'name': report.student.get_full_name()
                    },
                    'teacher': {
                        'id': report.teacher.id,
                        'name': report.teacher.get_full_name(),
                        'subject': getattr(report.teacher.teacher_profile, 'subject', 'Не указан') if hasattr(report.teacher, 'teacher_profile') else 'Не указан'
                    },
                    'period_start': report.period_start,
                    'period_end': report.period_end,
                    'overall_grade': report.overall_grade,
                    'progress_percentage': report.progress_percentage,
                    'attendance_percentage': report.attendance_percentage,
                    'behavior_rating': report.behavior_rating,
                    'recommendations': report.recommendations,
                    'concerns': report.concerns,
                    'achievements': report.achievements,
                    'created_at': report.created_at,
                    'sent_at': report.sent_at,
                    'read_at': report.read_at
                })
            
            return result
            
        except User.DoesNotExist:
            return []
        except Exception as e:
            print(f"Ошибка при получении отчетов для родителя: {e}")
            return []
    
    def mark_report_as_read(self, report_id: int, user_id: int) -> Dict[str, Any]:
        """
        Отметить отчет как прочитанный
        
        Args:
            report_id: ID отчета
            user_id: ID пользователя
            
        Returns:
            Результат операции
        """
        try:
            report = StudentReport.objects.get(id=report_id)
            user = User.objects.get(id=user_id)
            
            # Проверяем права доступа
            if user.role == User.Role.PARENT and report.parent != user:
                return {
                    'success': False,
                    'message': 'У вас нет прав на просмотр этого отчета'
                }
            elif user.role == User.Role.STUDENT and report.student != user:
                return {
                    'success': False,
                    'message': 'У вас нет прав на просмотр этого отчета'
                }
            
            # Отмечаем как прочитанный
            if not report.read_at:
                report.read_at = timezone.now()
                if report.status == StudentReport.Status.SENT:
                    report.status = StudentReport.Status.READ
                report.save()
            
            return {
                'success': True,
                'message': 'Отчет отмечен как прочитанный'
            }
            
        except StudentReport.DoesNotExist:
            return {
                'success': False,
                'message': 'Отчет не найден'
            }
        except User.DoesNotExist:
            return {
                'success': False,
                'message': 'Пользователь не найден'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Ошибка при обновлении статуса отчета: {str(e)}'
            }
    
    def generate_automatic_report(self, student_id: int, period_days: int = 30) -> Dict[str, Any]:
        """
        Автоматически сгенерировать отчет на основе данных о прогрессе
        
        Args:
            student_id: ID студента
            period_days: Период в днях для анализа
            
        Returns:
            Результат генерации отчета
        """
        try:
            student = User.objects.get(id=student_id, role=User.Role.STUDENT)
            
            # Определяем период
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=period_days)
            
            # Получаем материалы преподавателя, назначенные студенту
            teacher_materials = Material.objects.filter(
                author=self.teacher,
                assigned_to=student,
                status=Material.Status.ACTIVE
            )
            
            # Получаем прогресс за период
            progress_records = MaterialProgress.objects.filter(
                student=student,
                material__in=teacher_materials,
                last_accessed__date__range=[start_date, end_date]
            )
            
            # Вычисляем метрики
            total_materials = teacher_materials.count()
            completed_materials = progress_records.filter(is_completed=True).count()
            avg_progress = progress_records.aggregate(avg=Avg('progress_percentage'))['avg'] or 0
            total_time_spent = progress_records.aggregate(total=Sum('time_spent'))['total'] or 0
            
            # Определяем общую оценку
            if avg_progress >= 90:
                overall_grade = 'Отлично'
            elif avg_progress >= 75:
                overall_grade = 'Хорошо'
            elif avg_progress >= 60:
                overall_grade = 'Удовлетворительно'
            else:
                overall_grade = 'Требует внимания'
            
            # Создаем автоматический отчет
            report_data = {
                'title': f'Автоматический отчет за {period_days} дней',
                'description': f'Отчет сгенерирован автоматически на основе данных о прогрессе',
                'report_type': StudentReport.ReportType.PROGRESS,
                'period_start': start_date,
                'period_end': end_date,
                'content': {
                    'total_materials': total_materials,
                    'completed_materials': completed_materials,
                    'average_progress': round(avg_progress, 2),
                    'total_time_spent': total_time_spent,
                    'period_days': period_days
                },
                'overall_grade': overall_grade,
                'progress_percentage': int(avg_progress),
                'attendance_percentage': 100,  # Пока не реализовано
                'behavior_rating': 8,  # Пока не реализовано
                'recommendations': self._generate_recommendations(avg_progress, completed_materials, total_materials),
                'achievements': self._generate_achievements(completed_materials, avg_progress)
            }
            
            return self.create_student_report(student_id, report_data)
            
        except User.DoesNotExist:
            return {
                'success': False,
                'message': 'Студент не найден'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Ошибка при генерации отчета: {str(e)}'
            }
    
    def _send_parent_notification(self, report: StudentReport) -> None:
        """
        Отправить уведомление родителю о новом отчете
        
        Args:
            report: Отчет о студенте
        """
        try:
            if not report.parent:
                return
            
            # Формируем сообщение
            message = f"""
📊 Новый отчет о вашем ребенке

👤 Студент: {report.student.get_full_name()}
👨‍🏫 Преподаватель: {report.teacher.get_full_name()}
📅 Период: {report.period_start} - {report.period_end}
📋 Тип отчета: {report.get_report_type_display()}

📈 Прогресс: {report.progress_percentage}%
🎯 Общая оценка: {report.overall_grade or 'Не указана'}
⭐ Оценка поведения: {report.behavior_rating}/10

{report.description if report.description else ''}

Рекомендации:
{report.recommendations if report.recommendations else 'Не указаны'}

Достижения:
{report.achievements if report.achievements else 'Не указаны'}
            """.strip()
            
            # Отправляем уведомление
            self.telegram_service.send_message(message)
            
        except Exception as e:
            print(f"Ошибка при отправке уведомления родителю: {e}")
    
    def _generate_recommendations(self, avg_progress: float, completed: int, total: int) -> str:
        """
        Генерировать рекомендации на основе прогресса
        
        Args:
            avg_progress: Средний прогресс
            completed: Количество завершенных материалов
            total: Общее количество материалов
            
        Returns:
            Строка с рекомендациями
        """
        recommendations = []
        
        if avg_progress < 50:
            recommendations.append("Рекомендуется увеличить время изучения материалов")
            recommendations.append("Стоит обратиться за дополнительной помощью к преподавателю")
        elif avg_progress < 75:
            recommendations.append("Хороший прогресс, можно увеличить интенсивность обучения")
        else:
            recommendations.append("Отличные результаты! Продолжайте в том же духе")
        
        completion_rate = (completed / total * 100) if total > 0 else 0
        if completion_rate < 30:
            recommendations.append("Рекомендуется завершить больше материалов для лучшего понимания темы")
        
        return " ".join(recommendations)
    
    def _generate_achievements(self, completed: int, avg_progress: float) -> str:
        """
        Генерировать достижения на основе прогресса
        
        Args:
            completed: Количество завершенных материалов
            avg_progress: Средний прогресс
            
        Returns:
            Строка с достижениями
        """
        achievements = []
        
        if completed > 0:
            achievements.append(f"Завершено {completed} материалов")
        
        if avg_progress >= 90:
            achievements.append("Превосходные результаты в обучении")
        elif avg_progress >= 75:
            achievements.append("Хорошие результаты в обучении")
        elif avg_progress >= 50:
            achievements.append("Стабильный прогресс в обучении")
        
        if completed >= 5:
            achievements.append("Активное изучение материалов")
        
        return " ".join(achievements) if achievements else "Достижения будут отображаться по мере обучения"
