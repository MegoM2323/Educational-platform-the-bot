"""
T_ASSIGN_004: URL configuration for grading rubric endpoints

Register GradingRubricViewSet and RubricCriterionViewSet with Django REST Framework router.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_rubric import GradingRubricViewSet, RubricCriterionViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'rubrics', GradingRubricViewSet, basename='rubric')
router.register(r'criteria', RubricCriterionViewSet, basename='criterion')

# Include router URLs
urlpatterns = [
    path('', include(router.urls)),
]
