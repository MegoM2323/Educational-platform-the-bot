from rest_framework import status, permissions, generics, viewsets
from rest_framework.decorators import action
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
        print(f"[IsTutor.has_permission] Called for method: {request.method}")
        print(f"[IsTutor] Checking permission")
        print(f"[IsTutor] Authorization header: {request.META.get('HTTP_AUTHORIZATION', 'NOT SET')}")
        print(f"[IsTutor] User: {request.user}")
        print(f"[IsTutor] User type: {type(request.user)}")
        
        if not request.user.is_authenticated:
            print(f"[IsTutor] User not authenticated")
            print(f"[IsTutor] User object: {request.user}")
            return False
        
        user_role = getattr(request.user, 'role', None)
        is_staff = getattr(request.user, 'is_staff', False)
        is_superuser = getattr(request.user, 'is_superuser', False)
        
        print(f"[IsTutor] User: {request.user.username}, ID: {request.user.id}, Role: {user_role}, is_staff: {is_staff}, is_superuser: {is_superuser}")
        
        # Разрешаем доступ для тьюторов или администраторов
        result = (
            user_role == User.Role.TUTOR or 
            is_staff or 
            is_superuser
        )
        
        if not result:
            print(f"[IsTutor] Permission denied: user role '{user_role}' is not tutor and user is not staff/superuser")
        
        print(f"[IsTutor] Access granted: {result}")
        return result


class TutorStudentsViewSet(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication, CSRFExemptSessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTutor]

    def list(self, request):
        print(f"[TutorStudentsViewSet.list] Request received")
        print(f"[TutorStudentsViewSet.list] User: {request.user}")
        print(f"[TutorStudentsViewSet.list] User authenticated: {request.user.is_authenticated}")
        print(f"[TutorStudentsViewSet.list] User role: {getattr(request.user, 'role', None)}")
        print(f"[TutorStudentsViewSet.list] User is_staff: {getattr(request.user, 'is_staff', False)}")
        print(f"[TutorStudentsViewSet.list] User is_superuser: {getattr(request.user, 'is_superuser', False)}")
        
        # Показываем всех учеников тьютора:
        # 1) у кого в профиле явно указан этот тьютор (tutor=request.user)
        # 2) кого этот тьютор создавал (user__created_by_tutor=request.user)
        # Используем общий фильтр, который работает и для тьюторов, и для администраторов
        students = (
            StudentProfile.objects
            .filter(Q(tutor=request.user) | Q(user__created_by_tutor=request.user))
            .select_related('user', 'tutor', 'parent')
            .distinct()  # Избегаем дубликатов, если оба условия выполнены
        )
        
        print(f"[TutorStudentsViewSet.list] Found {students.count()} students")
        print(f"[TutorStudentsViewSet.list] Students: {[s.user.username for s in students]}")
        
        serializer = TutorStudentSerializer(students, many=True)
        print(f"[TutorStudentsViewSet.list] Serialized data: {serializer.data}")
        
        return Response({
            'success': True,
            'data': serializer.data,
            'timestamp': str(timezone.now())
        })

    def create(self, request):
        print(f"[TutorStudentsViewSet.create] Request received")
        print(f"[TutorStudentsViewSet.create] User: {request.user}")
        print(f"[TutorStudentsViewSet.create] User authenticated: {request.user.is_authenticated}")
        print(f"[TutorStudentsViewSet.create] User role: {getattr(request.user, 'role', None)}")
        print(f"[TutorStudentsViewSet.create] Request data: {request.data}")
        
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
            print(f"[TutorStudentsViewSet.create] PermissionError: {e}")
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            print(f"[TutorStudentsViewSet.create] Exception: {e}")
            import traceback
            print(f"[TutorStudentsViewSet.create] Traceback: {traceback.format_exc()}")
            return Response({'detail': f'Ошибка создания ученика: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student_profile = student_user.student_profile
        except StudentProfile.DoesNotExist:
            print(f"[TutorStudentsViewSet.create] StudentProfile not found for user {student_user.id}")
            return Response({'detail': 'Профиль студента не был создан'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        print(f"[TutorStudentsViewSet.create] Student profile created: {student_profile.id}")
        print(f"[TutorStudentsViewSet.create] Student profile tutor: {student_profile.tutor}")
        print(f"[TutorStudentsViewSet.create] Student profile parent: {student_profile.parent} (id: {student_profile.parent_id})")
        print(f"[TutorStudentsViewSet.create] Student user created_by_tutor: {student_user.created_by_tutor}")
        print(f"[TutorStudentsViewSet.create] Request user: {request.user}")
        
        # Проверяем связь родитель-ребенок
        if parent_user:
            print(f"[TutorStudentsViewSet.create] Parent user: {parent_user.username}, role: {parent_user.role}")
            try:
                parent_profile = parent_user.parent_profile
                children = list(parent_profile.children)
                print(f"[TutorStudentsViewSet.create] ParentProfile exists: True, children count: {len(children)}")
                print(f"[TutorStudentsViewSet.create] Children: {[c.username for c in children]}")
            except Exception as e:
                print(f"[TutorStudentsViewSet.create] Error getting ParentProfile: {e}")
        
        response = {
            'student': TutorStudentSerializer(student_profile).data,
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
            print(f"[TutorStudentsViewSet.retrieve] Error: {e}")
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
            print(f"[TutorStudentsViewSet.subjects] Error: {e}")
            return Response({'detail': f'Ошибка получения ученика: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        if request.method.lower() == 'get':
            from materials.models import SubjectEnrollment
            enrollments = SubjectEnrollment.objects.filter(student=student_profile.user).select_related('subject', 'teacher')
            return Response(SubjectEnrollmentSerializer(enrollments, many=True).data)

        assign_serializer = SubjectAssignSerializer(data=request.data)
        assign_serializer.is_valid(raise_exception=True)
        subject = assign_serializer.validated_data['subject']
        teacher = assign_serializer.validated_data['teacher']

        try:
            enrollment = SubjectAssignmentService.assign_subject(
                tutor=request.user,
                student=student_profile.user,
                subject=subject,
                teacher=teacher,
            )
            return Response(SubjectEnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)
        except PermissionError as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"[TutorStudentsViewSet.subjects] Error assigning subject: {e}")
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
            print(f"[TutorStudentsViewSet.unassign_subject] Error getting student: {e}")
            return Response({'detail': f'Ошибка получения ученика: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({'detail': 'Предмет не найден'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"[TutorStudentsViewSet.unassign_subject] Error getting subject: {e}")
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
            print(f"[TutorStudentsViewSet.unassign_subject] Error unassigning subject: {e}")
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
            print(f"[TutorStudentsViewSet.assign_subjects_bulk] Error getting student: {e}")
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
                print(f"[TutorStudentsViewSet.assign_subjects_bulk] Error assigning subject {subject.id}: {e}")
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

    


