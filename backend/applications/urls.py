from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    # Public endpoints
    path('submit/', views.ApplicationSubmitView.as_view(), name='application-submit'),
    path('status/<uuid:token>/', views.application_status, name='application-status'),
    
    # Administrative endpoints (require admin authentication)
    path('', views.ApplicationListView.as_view(), name='application-list'),
    path('<int:pk>/', views.ApplicationDetailView.as_view(), name='application-detail'),
    path('<int:pk>/approve/', views.ApplicationApproveView.as_view(), name='application-approve'),
    path('<int:pk>/reject/', views.ApplicationRejectView.as_view(), name='application-reject'),
    path('statistics/', views.application_statistics, name='application-statistics'),
    path('test-telegram/', views.test_telegram_connection, name='test-telegram'),
]
