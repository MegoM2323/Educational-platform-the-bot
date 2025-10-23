from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    # Публичные эндпоинты
    path('create/', views.ApplicationCreateView.as_view(), name='application-create'),
    
    # Административные эндпоинты (требуют авторизации)
    path('', views.ApplicationListView.as_view(), name='application-list'),
    path('<int:pk>/', views.ApplicationDetailView.as_view(), name='application-detail'),
    path('<int:pk>/status/', views.ApplicationStatusUpdateView.as_view(), name='application-status-update'),
    path('statistics/', views.application_statistics, name='application-statistics'),
    path('test-telegram/', views.test_telegram_connection, name='test-telegram'),
]
