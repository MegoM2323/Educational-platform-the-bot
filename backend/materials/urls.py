from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'subjects', views.SubjectViewSet)
router.register(r'materials', views.MaterialViewSet)
router.register(r'progress', views.MaterialProgressViewSet)
router.register(r'comments', views.MaterialCommentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
