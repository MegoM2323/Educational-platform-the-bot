"""
YooKassa API mocks and fixtures for testing payments
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_yookassa_config():
    """Mock YooKassa Configuration"""
    with patch('payments.services.Configuration') as mock_config:
        mock_config.account_id = 'test_shop_id'
        mock_config.secret_key = 'test_secret_key'
        yield mock_config


@pytest.fixture
def mock_yookassa_payment_create():
    """Mock YooKassa Payment.create() method"""
    mock_payment = MagicMock()
    mock_payment.id = 'test-payment-id-12345'
    mock_payment.status = 'pending'
    mock_payment.paid = False
    mock_payment.amount = MagicMock()
    mock_payment.amount.value = '100.00'
    mock_payment.amount.currency = 'RUB'
    mock_payment.confirmation = MagicMock()
    mock_payment.confirmation.type = 'redirect'
    mock_payment.confirmation.confirmation_url = 'https://yookassa.ru/checkout/test-123'
    mock_payment.created_at = timezone.now().isoformat()
    mock_payment.metadata = {}

    with patch('payments.services.Payment.create', return_value=mock_payment) as mock:
        yield mock


@pytest.fixture
def mock_yookassa_payment_find():
    """Mock YooKassa Payment.find_one() method"""
    def create_payment_mock(payment_id, status='succeeded', paid=True):
        mock_payment = MagicMock()
        mock_payment.id = payment_id
        mock_payment.status = status
        mock_payment.paid = paid
        mock_payment.amount = MagicMock()
        mock_payment.amount.value = '100.00'
        mock_payment.amount.currency = 'RUB'
        mock_payment.created_at = timezone.now().isoformat()
        if paid:
            mock_payment.captured_at = timezone.now().isoformat()
        mock_payment.metadata = {}
        return mock_payment

    with patch('payments.services.Payment.find_one', side_effect=create_payment_mock) as mock:
        yield mock


@pytest.fixture
def mock_yookassa_refund_create():
    """Mock YooKassa Refund.create() method"""
    mock_refund = MagicMock()
    mock_refund.id = 'test-refund-id-12345'
    mock_refund.status = 'succeeded'
    mock_refund.amount = MagicMock()
    mock_refund.amount.value = '100.00'
    mock_refund.amount.currency = 'RUB'
    mock_refund.created_at = timezone.now().isoformat()
    mock_refund.payment_id = 'test-payment-id-12345'

    with patch('payments.services.Refund.create', return_value=mock_refund) as mock:
        yield mock


@pytest.fixture
def yookassa_webhook_payment_succeeded():
    """YooKassa webhook payload for payment.succeeded event"""
    return {
        'type': 'notification',
        'event': 'payment.succeeded',
        'object': {
            'id': 'test-payment-webhook-123',
            'status': 'succeeded',
            'paid': True,
            'amount': {
                'value': '100.00',
                'currency': 'RUB'
            },
            'created_at': timezone.now().isoformat(),
            'captured_at': timezone.now().isoformat(),
            'metadata': {
                'payment_id': '1',
                'enrollment_id': '1'
            },
            'payment_method': {
                'type': 'bank_card',
                'id': 'test-pm-123',
                'saved': False,
                'card': {
                    'first6': '555555',
                    'last4': '4444',
                    'expiry_month': '12',
                    'expiry_year': '2025',
                    'card_type': 'MasterCard'
                }
            },
            'confirmation': {
                'type': 'redirect',
                'return_url': 'http://localhost:8080/payment/success'
            }
        }
    }


@pytest.fixture
def yookassa_webhook_payment_canceled():
    """YooKassa webhook payload for payment.canceled event"""
    return {
        'type': 'notification',
        'event': 'payment.canceled',
        'object': {
            'id': 'test-payment-webhook-123',
            'status': 'canceled',
            'paid': False,
            'amount': {
                'value': '100.00',
                'currency': 'RUB'
            },
            'created_at': timezone.now().isoformat(),
            'canceled_at': timezone.now().isoformat(),
            'cancellation_details': {
                'party': 'yoo_money',
                'reason': 'expired_on_confirmation'
            },
            'metadata': {
                'payment_id': '1',
                'enrollment_id': '1'
            }
        }
    }


@pytest.fixture
def yookassa_webhook_payment_waiting_for_capture():
    """YooKassa webhook payload for payment.waiting_for_capture event"""
    return {
        'type': 'notification',
        'event': 'payment.waiting_for_capture',
        'object': {
            'id': 'test-payment-webhook-123',
            'status': 'waiting_for_capture',
            'paid': True,
            'amount': {
                'value': '100.00',
                'currency': 'RUB'
            },
            'created_at': timezone.now().isoformat(),
            'expires_at': (timezone.now() + timedelta(hours=1)).isoformat(),
            'metadata': {
                'payment_id': '1',
                'enrollment_id': '1'
            }
        }
    }


@pytest.fixture
def yookassa_webhook_refund_succeeded():
    """YooKassa webhook payload for refund.succeeded event"""
    return {
        'type': 'notification',
        'event': 'refund.succeeded',
        'object': {
            'id': 'test-refund-webhook-123',
            'status': 'succeeded',
            'amount': {
                'value': '100.00',
                'currency': 'RUB'
            },
            'created_at': timezone.now().isoformat(),
            'payment_id': 'test-payment-webhook-123'
        }
    }


@pytest.fixture
def mock_yookassa_all():
    """Mock all YooKassa API methods at once for convenience"""
    with patch('payments.services.Configuration') as mock_config, \
         patch('payments.services.Payment') as mock_payment_class:

        # Setup Configuration
        mock_config.account_id = 'test_shop_id'
        mock_config.secret_key = 'test_secret_key'

        # Setup Payment.create
        mock_payment = MagicMock()
        mock_payment.id = 'test-payment-id-12345'
        mock_payment.status = 'pending'
        mock_payment.paid = False
        mock_payment.amount = MagicMock()
        mock_payment.amount.value = '100.00'
        mock_payment.amount.currency = 'RUB'
        mock_payment.confirmation = MagicMock()
        mock_payment.confirmation.type = 'redirect'
        mock_payment.confirmation.confirmation_url = 'https://yookassa.ru/checkout/test-123'
        mock_payment.created_at = timezone.now().isoformat()
        mock_payment.metadata = {}

        mock_payment_class.create.return_value = mock_payment
        mock_payment_class.find_one.return_value = mock_payment

        yield {
            'config': mock_config,
            'payment_class': mock_payment_class,
            'payment': mock_payment
        }
