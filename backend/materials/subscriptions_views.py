from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .models import SubjectEnrollment
from accounts.permissions import IsParent

User = get_user_model()


class CancelSubscriptionView(APIView):
    """
    View для отмены подписок на предметы.

    POST /api/subscriptions/<subscription_id>/cancel/ - отменить подписку
    """

    permission_classes = [IsAuthenticated, IsParent]

    def post(self, request, subscription_id=None):
        """Отменить подписку на предмет"""
        try:
            enrollment = SubjectEnrollment.objects.get(id=subscription_id)
        except SubjectEnrollment.DoesNotExist:
            return Response(
                {"error": "Enrollment not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Проверяем что это подписка ребенка этого родителя
        from accounts.models import StudentProfile

        try:
            student_profile = StudentProfile.objects.get(user=enrollment.student)
            if student_profile.parent != request.user:
                return Response(
                    {"error": "You do not have permission to cancel this subscription"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except StudentProfile.DoesNotExist:
            return Response(
                {"error": "Student profile not found"}, status=status.HTTP_403_FORBIDDEN
            )

        # Проверяем что статус не "cancelled"
        if enrollment.status == "cancelled":
            return Response(
                {"error": "Subscription is already cancelled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Отменяем подписку
        enrollment.status = "cancelled"
        enrollment.save()

        return Response(
            {
                "success": True,
                "message": "Subscription cancelled successfully",
                "enrollment_id": enrollment.id,
                "status": enrollment.status,
            },
            status=status.HTTP_200_OK,
        )
