from django.urls import path
from . import parent_dashboard_views

urlpatterns = [
    path('', parent_dashboard_views.ParentDashboardView.as_view(), name='parent-dashboard'),
    path('children/', parent_dashboard_views.ParentChildrenView.as_view(), name='parent-children'),
    path('children/<int:child_id>/subjects/', parent_dashboard_views.get_child_subjects, name='child-subjects'),
    path('children/<int:child_id>/progress/', parent_dashboard_views.get_child_progress, name='child-progress'),
    path('children/<int:child_id>/teachers/', parent_dashboard_views.get_child_teachers, name='child-teachers'),
    path('children/<int:child_id>/payments/', parent_dashboard_views.get_payment_status, name='child-payments'),
    path('children/<int:child_id>/payment/<int:enrollment_id>/', parent_dashboard_views.initiate_payment, name='initiate-payment'),
    path('payments/', parent_dashboard_views.parent_payments, name='parent-payments'),
    path('payments/pending/', parent_dashboard_views.parent_pending_payments, name='parent-pending-payments'),
    path('reports/', parent_dashboard_views.get_reports, name='parent-reports'),
    path('reports/<int:child_id>/', parent_dashboard_views.get_reports, name='parent-child-reports'),
    path('children/<int:child_id>/subscription/<int:enrollment_id>/cancel/', parent_dashboard_views.cancel_subscription, name='cancel-subscription'),
]
