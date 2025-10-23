from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'assignments', views.AssignmentViewSet)
router.register(r'submissions', views.AssignmentSubmissionViewSet)
router.register(r'questions', views.AssignmentQuestionViewSet)
router.register(r'answers', views.AssignmentAnswerViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
