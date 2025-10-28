from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import SubjectEnrollment, Material, MaterialSubmission, MaterialFeedback
from .serializers import (
    MaterialListSerializer,
    MaterialSubmissionSerializer,
    MaterialFeedbackSerializer,
)


User = get_user_model()


def _ensure_student(user: User):
    if getattr(user, "role", None) != User.Role.STUDENT:
        return Response({"error": "Доступ разрешен только студентам"}, status=status.HTTP_403_FORBIDDEN)
    return None


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_student_subjects(request):
    """
    GET /api/student/subjects/
    Возвращает список предметов, на которые зачислен студент, с информацией о преподавателе.
    """
    forbidden = _ensure_student(request.user)
    if forbidden:
        return forbidden

    enrollments = (
        SubjectEnrollment.objects.filter(student=request.user, is_active=True)
        .select_related("subject", "teacher")
        .order_by("subject__name")
    )

    result = []
    for e in enrollments:
        result.append(
            {
                "enrollment_id": e.id,
                "subject": {
                    "id": e.subject.id,
                    "name": e.subject.name,
                    "color": e.subject.color,
                },
                "teacher": {
                    "id": e.teacher.id,
                    "first_name": e.teacher.first_name,
                    "last_name": e.teacher.last_name,
                    "full_name": e.teacher.get_full_name(),
                },
                "enrolled_at": e.enrolled_at,
                "is_active": e.is_active,
            }
        )

    return Response(result)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_subject_materials(request, subject_id: int):
    """
    GET /api/student/subjects/{subject_id}/materials/
    Возвращает материалы по предмету, назначенные студенту или публичные.
    """
    forbidden = _ensure_student(request.user)
    if forbidden:
        return forbidden

    # Проверим наличие активной записи зачисления на предмет
    if not SubjectEnrollment.objects.filter(
        student=request.user, subject_id=subject_id, is_active=True
    ).exists():
        return Response({"error": "Вы не зачислены на этот предмет"}, status=status.HTTP_403_FORBIDDEN)

    materials = (
        Material.objects.filter(
            Q(assigned_to=request.user) | Q(is_public=True),
            status=Material.Status.ACTIVE,
            subject_id=subject_id,
        )
        .select_related("author", "subject")
        .prefetch_related("progress")
        .order_by("-created_at")
    )

    serializer = MaterialListSerializer(materials, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_subject_teacher(request, subject_id: int):
    """
    GET /api/student/subjects/{subject_id}/teacher/
    Возвращает информацию о преподавателе для предмета студента.
    """
    forbidden = _ensure_student(request.user)
    if forbidden:
        return forbidden

    enrollment = (
        SubjectEnrollment.objects.filter(
            student=request.user, subject_id=subject_id, is_active=True
        )
        .select_related("teacher")
        .first()
    )

    if not enrollment:
        return Response({"error": "Запись зачисления не найдена"}, status=status.HTTP_404_NOT_FOUND)

    teacher = enrollment.teacher
    data = {
        "id": teacher.id,
        "first_name": teacher.first_name,
        "last_name": teacher.last_name,
        "full_name": teacher.get_full_name(),
        "email": teacher.email,
    }
    return Response(data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def submit_material_submission(request, material_id: int):
    """
    POST /api/student/materials/{material_id}/submissions/
    Создать сабмишен по материалу (файл и/или текст).
    """
    forbidden = _ensure_student(request.user)
    if forbidden:
        return forbidden

    try:
        material = Material.objects.get(id=material_id)
    except Material.DoesNotExist:
        return Response({"error": "Материал не найден"}, status=status.HTTP_404_NOT_FOUND)

    # Проверка доступа к материалу
    if not (material.is_public or material.assigned_to.filter(id=request.user.id).exists()):
        return Response({"error": "Материал не назначен вам"}, status=status.HTTP_403_FORBIDDEN)

    # Один сабмишен на материал на текущей модели
    if MaterialSubmission.objects.filter(material=material, student=request.user).exists():
        return Response({"error": "Ответ уже отправлен"}, status=status.HTTP_400_BAD_REQUEST)

    payload = request.data.copy()
    payload["material"] = material.id

    serializer = MaterialSubmissionSerializer(data=payload, context={"request": request})
    if serializer.is_valid():
        submission = serializer.save(material=material, student=request.user)
        return Response(MaterialSubmissionSerializer(submission, context={"request": request}).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_student_submissions(request):
    """
    GET /api/student/submissions/
    Список сабмишенов текущего студента.
    """
    forbidden = _ensure_student(request.user)
    if forbidden:
        return forbidden

    submissions = (
        MaterialSubmission.objects.filter(student=request.user)
        .select_related("material")
        .order_by("-submitted_at")
    )
    serializer = MaterialSubmissionSerializer(submissions, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_submission_feedback(request, submission_id: int):
    """
    GET /api/student/submissions/{submission_id}/feedback/
    Получение фидбэка по сабмишену студента (если есть).
    """
    forbidden = _ensure_student(request.user)
    if forbidden:
        return forbidden

    try:
        submission = MaterialSubmission.objects.select_related("student").get(id=submission_id, student=request.user)
    except MaterialSubmission.DoesNotExist:
        return Response({"error": "Сабмишен не найден"}, status=status.HTTP_404_NOT_FOUND)

    feedback = MaterialFeedback.objects.filter(submission=submission).first()
    if not feedback:
        return Response({"error": "Фидбэк отсутствует"}, status=status.HTTP_404_NOT_FOUND)

    return Response(MaterialFeedbackSerializer(feedback, context={"request": request}).data)


