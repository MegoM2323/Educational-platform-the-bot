import logging
from rest_framework import status, permissions, generics, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from django.contrib.auth import get_user_model
from django.utils import timezone

from materials.models import Subject
from django.db.models import Q
from .models import StudentProfile
from .tutor_service import StudentCreationService, SubjectAssignmentService
from .tutor_serializers import (
    TutorStudentCreateSerializer,
    TutorStudentSerializer,
    SubjectAssignSerializer,
    SubjectEnrollmentSerializer,
    SubjectBulkAssignSerializer,
)
from .serializers import UserSerializer


logger = logging.getLogger(__name__)
User = get_user_model()


class CSRFExemptSessionAuthentication(SessionAuthentication):
    """
    Кастомный класс аутентификации, который отключает CSRF проверку для API views.
    Используется для POST запросов, где фронтенд использует токены.
    """
    def enforce_csrf(self, request):
        # Отключаем CSRF проверку для API запросов
        return


class IsTutor(permissions.BasePermission):
    """
    Разрешение для пользователей с ролью TUTOR или администраторов (staff/superuser).
    Администраторы имеют доступ ко всем функциям тьютора.
    """
    def has_permission(self, request, view):
        logger.debug(f"IsTutor permission check for method: {request.method}")
        logger.debug(f"Authorization header: {request.META.get('HTTP_AUTHORIZATION', 'NOT SET')}")
        logger.debug(f"User: {request.user}, type: {type(request.user)}")

        if not request.user.is_authenticated:
            logger.debug(f"User not authenticated: {request.user}")
            return False

        user_role = getattr(request.user, 'role', None)
        is_staff = getattr(request.user, 'is_staff', False)
        is_superuser = getattr(request.user, 'is_superuser', False)

        logger.debug(
            f"User: {request.user.username}, ID: {request.user.id}, "
            f"Role: {user_role}, is_staff: {is_staff}, is_superuser: {is_superuser}"
        )

        # Разрешаем доступ для тьюторов или администраторов
        result = (
            user_role == User.Role.TUTOR or
            is_staff or
            is_superuser
        )

        if not result:
            logger.warning(
                f"IsTutor permission denied: user role '{user_role}' is not tutor "
                f"and user is not staff/superuser"
            )

        logger.debug(f"IsTutor access granted: {result}")
        return result


class TutorStudentsViewSet(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication, CSRFExemptSessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTutor]

    def list(self, request):
        logger.info(f"TutorStudentsViewSet.list request from user: {request.user.username}")
        logger.debug(
            f"User authenticated: {request.user.is_authenticated}, "
            f"role: {getattr(request.user, 'role', None)}, "
            f"is_staff: {getattr(request.user, 'is_staff', False)}, "
            f"is_superuser: {getattr(request.user, 'is_superuser', False)}"
        )

        # Показываем всех учеников тьютора:
        # 1) у кого в профиле явно указан этот тьютор (tutor=request.user)
        # 2) кого этот тьютор создавал (user__created_by_tutor=request.user)
        # Используем общий фильтр, который работает и для тьюторов, и для администраторов
        # Принудительно получаем свежие данные из базы, не используя кеш

        # Сначала получаем queryset
        students_queryset = (
            StudentProfile.objects
            .filter(Q(tutor=request.user) | Q(user__created_by_tutor=request.user))
            .select_related('user', 'tutor', 'parent')
            .distinct()  # Избегаем дубликатов, если оба условия выполнены
            .order_by('-user__date_joined')  # Сортируем по дате создания (новые первыми)
        )

        # Преобразуем в список, чтобы выполнить запрос и получить свежие данные
        # Это гарантирует, что мы получаем актуальные данные из базы
        students_list = list(students_queryset)

        logger.info(f"Found {len(students_list)} students for user {request.user.username}")
        logger.debug(f"Students: {[s.user.username for s in students_list]}")

        # Проверяем связи для каждого студента
        for student in students_list:
            created_by = student.user.created_by_tutor_id if hasattr(student.user, 'created_by_tutor_id') else None
            logger.debug(f"Student {student.id}: tutor_id={student.tutor_id}, created_by_tutor_id={created_by}")

        # Сериализуем данные - get_subjects будет вызываться для каждого студента
        # и получать свежие данные из базы каждый раз
        serializer = TutorStudentSerializer(students_list, many=True)

        # Логируем информацию о предметах для каждого студента
        for student_data in serializer.data:
            subjects_count = len(student_data.get('subjects', []))
            student_id = student_data.get('id')
            student_name = student_data.get('full_name')
            logger.debug(f"Student {student_id} ({student_name}) has {subjects_count} subjects")
            if subjects_count > 0:
                for subject in student_data.get('subjects', []):
                    logger.debug(
                        f"  - {subject.get('name')} (teacher: {subject.get('teacher_name')}, "
                        f"enrollment_id: {subject.get('enrollment_id')})"
                    )

        # Возвращаем просто массив данных, как ожидает фронтенд
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        logger.info(f"TutorStudentsViewSet.create request from user: {request.user.username}")
        logger.debug(
            f"User authenticated: {request.user.is_authenticated}, "
            f"role: {getattr(request.user, 'role', None)}"
        )
        logger.debug(f"Request data: {request.data}")

        serializer = TutorStudentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
            student_user, parent_user, student_creds, parent_creds = StudentCreationService.create_student_with_parent(
                tutor=request.user,
                student_first_name=data['first_name'],
                student_last_name=data['last_name'],
                grade=data['grade'],
                goal=data.get('goal', ''),
                parent_first_name=data['parent_first_name'],
                parent_last_name=data['parent_last_name'],
                parent_email=data.get('parent_email', ''),
                parent_phone=data.get('parent_phone', ''),
            )
        except PermissionError as e:
            logger.error(f"PermissionError creating student: {e}")
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.exception(f"Exception creating student: {e}")
            return Response({'detail': f'Ошибка создания ученика: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Принудительно перезагружаем студента из базы для получения свежих данных
            student_profile = StudentProfile.objects.select_related('user', 'tutor', 'parent').get(id=student_user.student_profile.id)
        except StudentProfile.DoesNotExist:
            logger.error(f"StudentProfile not found for user {student_user.id}")
            return Response({'detail': 'Профиль студента не был создан'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Принудительно обновляем данные из базы
        student_profile.refresh_from_db()
        student_user.refresh_from_db()

        logger.info(f"Student profile created: id={student_profile.id}")
        logger.debug(
            f"Student profile details - tutor_id: {student_profile.tutor_id}, "
            f"parent_id: {student_profile.parent_id}"
        )
        created_by = student_user.created_by_tutor_id if hasattr(student_user, 'created_by_tutor_id') else None
        logger.debug(f"Student user created_by_tutor_id: {created_by}, request.user.id: {request.user.id}")

        # Проверяем, что студент действительно виден в списке студентов этого тьютора
        # Это гарантирует, что связи установлены правильно
        students_count = StudentProfile.objects.filter(
            Q(id=student_profile.id) &
            (Q(tutor=request.user) | Q(user__created_by_tutor=request.user))
        ).count()
        logger.info(f"Student visibility check: {students_count} students found (should be 1)")

        if students_count == 0:
            logger.warning(
                f"Created student is not visible in tutor's student list! "
                f"tutor_id={student_profile.tutor_id}, request.user.id={request.user.id}, "
                f"created_by_tutor_id={created_by}"
            )

        # Проверяем связь родитель-ребенок
        if parent_user:
            logger.debug(f"Parent user: {parent_user.username}, role: {parent_user.role}")
            try:
                parent_profile = parent_user.parent_profile
                children = list(parent_profile.children)
                logger.debug(f"ParentProfile exists, children count: {len(children)}")
                logger.debug(f"Children: {[c.username for c in children]}")
            except Exception as e:
                logger.error(f"Error getting ParentProfile: {e}")

        # Сериализуем данные студента - это гарантирует, что предметы тоже будут загружены
        student_data = TutorStudentSerializer(student_profile).data
        logger.debug(
            f"Serialized student data: id={student_data.get('id')}, "
            f"name={student_data.get('full_name')}, "
            f"subjects_count={len(student_data.get('subjects', []))}"
        )
        
        response = {
            'student': student_data,
            'parent': {
                'id': parent_user.id,
                'full_name': parent_user.get_full_name() or parent_user.username,
            },
            'credentials': {
                'student': {
                    'username': student_creds.username,
                    'password': student_creds.password,
                },
                'parent': {
                    'username': parent_creds.username,
                    'password': parent_creds.password,
                },
            },
        }
        return Response(response, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        try:
            # Проверяем, что ученик принадлежит тьютору
            # Проверяем через tutor в профиле или через created_by_tutor в User
            profile = StudentProfile.objects.select_related('user', 'tutor', 'parent').get(
                Q(id=pk) & (Q(tutor=request.user) | Q(user__created_by_tutor=request.user))
            )
        except StudentProfile.DoesNotExist:
            return Response({'detail': 'Ученик не найден или не принадлежит вам'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving student: {e}")
            return Response({'detail': f'Ошибка получения ученика: {e}'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TutorStudentSerializer(profile).data)

    @action(detail=True, methods=['post', 'get'], url_path='subjects')
    def subjects(self, request, pk=None):
        # pk — это id StudentProfile
        try:
            # Проверяем, что ученик принадлежит тьютору
            student_profile = StudentProfile.objects.select_related('user').get(
                Q(id=pk) & (Q(tutor=request.user) | Q(user__created_by_tutor=request.user))
            )
        except StudentProfile.DoesNotExist:
            return Response({'detail': 'Ученик не найден или не принадлежит вам'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting student for subjects operation: {e}")
            return Response({'detail': f'Ошибка получения ученика: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        if request.method.lower() == 'get':
            from materials.models import SubjectEnrollment
            enrollments = SubjectEnrollment.objects.filter(student=student_profile.user).select_related('subject', 'teacher')
            return Response(SubjectEnrollmentSerializer(enrollments, many=True).data)

        assign_serializer = SubjectAssignSerializer(data=request.data)
        assign_serializer.is_valid(raise_exception=True)
        subject = assign_serializer.validated_data['subject']
        teacher = assign_serializer.validated_data.get('teacher')

        logger.info(
            f"Assigning subject: subject_id={subject.id}, teacher_id={teacher.id if teacher else None}, "
            f"student_id={student_profile.user.id}"
        )
        
        try:
            # Создаем или обновляем enrollment
            enrollment = SubjectAssignmentService.assign_subject(
                tutor=request.user,
                student=student_profile.user,
                subject=subject,
                teacher=teacher,
            )
            logger.info(
                f"Enrollment created/updated: id={enrollment.id}, is_active={enrollment.is_active}, "
                f"student_id={student_profile.user.id}, subject_id={subject.id}, teacher_id={teacher.id}"
            )

            # Принудительно перезагружаем enrollment из базы с актуальными данными
            from materials.models import SubjectEnrollment

            # Перезагружаем enrollment с актуальными данными
            enrollment = SubjectEnrollment.objects.select_related(
                'subject', 'teacher', 'student'
            ).get(id=enrollment.id)

            logger.debug(f"Reloaded enrollment: id={enrollment.id}, is_active={enrollment.is_active}")

            # Проверяем, сколько всего активных enrollments у этого студента
            # Это поможет убедиться, что enrollment действительно создан
            all_enrollments = list(SubjectEnrollment.objects.filter(
                student=student_profile.user,
                is_active=True
            ).values_list('id', flat=True).order_by('-enrolled_at', '-id'))
            logger.debug(
                f"Student {student_profile.user.id} now has {len(all_enrollments)} "
                f"active enrollments: {all_enrollments}"
            )

            # Проверяем, что новый enrollment в списке
            if enrollment.id not in all_enrollments:
                logger.warning(f"Enrollment {enrollment.id} not found in active enrollments list!")
            else:
                logger.debug(f"Enrollment {enrollment.id} confirmed in active enrollments list")
            
            # Принудительно обновляем данные из базы для студента
            student_profile.refresh_from_db()
            student_profile.user.refresh_from_db()

            # Инвалидируем кэш родителя для обновления дашборда
            try:
                from materials.cache_utils import DashboardCacheManager
                cache_manager = DashboardCacheManager()

                # Получаем родителя студента и инвалидируем его кэш
                parent = getattr(student_profile, 'parent', None)
                if parent:
                    cache_manager.invalidate_parent_cache(parent.id)
                    logger.info(
                        f"Parent cache invalidated: parent_id={parent.id}, "
                        f"student_id={student_profile.user.id}, enrollment_id={enrollment.id}"
                    )
            except Exception as e:
                logger.warning(f"Failed to invalidate parent cache: {e}")

            # Возвращаем данные enrollment
            enrollment_data = SubjectEnrollmentSerializer(enrollment).data
            logger.debug(f"Returning enrollment data: {enrollment_data}")

            return Response(enrollment_data, status=status.HTTP_200_OK)
        except PermissionError as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error assigning subject: {e}")
            return Response({'detail': f'Ошибка назначения предмета: {e}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='subjects/(?P<subject_id>[^/.]+)')
    def unassign_subject(self, request, pk=None, subject_id=None):
        try:
            # Проверяем, что ученик принадлежит тьютору
            student_profile = StudentProfile.objects.select_related('user').get(
                Q(id=pk) & (Q(tutor=request.user) | Q(user__created_by_tutor=request.user))
            )
        except StudentProfile.DoesNotExist:
            return Response({'detail': 'Ученик не найден или не принадлежит вам'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting student for unassign: {e}")
            return Response({'detail': f'Ошибка получения ученика: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({'detail': 'Предмет не найден'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting subject for unassign: {e}")
            return Response({'detail': f'Ошибка получения предмета: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            SubjectAssignmentService.unassign_subject(
                tutor=request.user,
                student=student_profile.user,
                subject=subject,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PermissionError as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error unassigning subject: {e}")
            return Response({'detail': f'Ошибка отмены назначения предмета: {e}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='subjects/bulk')
    def assign_subjects_bulk(self, request, pk=None):
        """Массовое назначение нескольких предметов одному ученику.
        Тело запроса: {"items": [{"subject_id": int, "teacher_id": int|null}, ...]}
        Возвращает список созданных/актуализированных зачислений.
        """
        try:
            # Проверяем, что ученик принадлежит тьютору
            student_profile = StudentProfile.objects.select_related('user').get(
                Q(id=pk) & (Q(tutor=request.user) | Q(user__created_by_tutor=request.user))
            )
        except StudentProfile.DoesNotExist:
            return Response({'detail': 'Ученик не найден или не принадлежит вам'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting student for bulk assign: {e}")
            return Response({'detail': f'Ошибка получения ученика: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SubjectBulkAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        enrollments = []
        errors = []
        for item in serializer.validated_data['items']:
            subject = item['subject']
            teacher = item.get('teacher')
            try:
                enrollment = SubjectAssignmentService.assign_subject(
                    tutor=request.user,
                    student=student_profile.user,
                    subject=subject,
                    teacher=teacher,
                )
                enrollments.append(enrollment)
            except (PermissionError, ValueError) as e:
                errors.append(f"Предмет {subject.name}: {str(e)}")
            except Exception as e:
                logger.error(f"Error assigning subject {subject.id} in bulk: {e}")
                errors.append(f"Предмет {subject.name}: Ошибка назначения")

        if errors and not enrollments:
            return Response({'detail': 'Ошибки при назначении предметов', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        
        if errors:
            return Response({
                'enrollments': SubjectEnrollmentSerializer(enrollments, many=True).data,
                'errors': errors,
                'warning': 'Некоторые предметы не были назначены'
            }, status=status.HTTP_200_OK)

        return Response(SubjectEnrollmentSerializer(enrollments, many=True).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated, IsTutor])
def list_teachers(request):
    """
    Получить список всех преподавателей для тьютора.
    Доступно только для тьюторов и администраторов.
    Возвращает только активных пользователей с ролью TEACHER (исключает админов и других ролей).
    """
    try:
        # Получаем только активных пользователей с ролью TEACHER
        # Явно исключаем админов и других ролей
        teachers = User.objects.filter(
            role=User.Role.TEACHER,  # Только преподаватели
            is_active=True,  # Только активные
            is_staff=False,  # Исключаем администраторов (is_staff=True)
            is_superuser=False  # Исключаем суперпользователей
        ).order_by('first_name', 'last_name', 'email')

        logger.info(
            f"Found {teachers.count()} teachers (role=TEACHER, is_active=True, "
            f"is_staff=False, is_superuser=False) for tutor {request.user.username}"
        )

        # Логируем для отладки
        for teacher in teachers[:5]:  # Логируем первые 5 для проверки
            logger.debug(
                f"Teacher: {teacher.username} (role={teacher.role}, is_staff={teacher.is_staff}, "
                f"is_superuser={teacher.is_superuser})"
            )

        # Сериализуем данные - UserSerializer должен правильно обработать всех преподавателей
        serializer = UserSerializer(teachers, many=True)

        # Возвращаем массив напрямую
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception(f"Error getting teachers list: {e}")
        return Response(
            {'error': f'Ошибка получения списка преподавателей: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    


