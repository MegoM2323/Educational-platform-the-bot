from django.urls import path
from .subscriptions_views import CancelSubscriptionView

urlpatterns = [
    path('<int:subscription_id>/cancel/', CancelSubscriptionView.as_view(), name='cancel-subscription'),
]
