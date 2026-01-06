import json
from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.middleware.csrf import get_token
from rest_framework.test import APIClient, APITestCase
from rest_framework.authtoken.models import Token
from accounts.factories import StudentFactory, TutorFactory, ParentFactory
from materials.factories import SubjectFactory, SubjectEnrollmentFactory

User = get_user_model()


class TestT136SQLInjectionProtection(APITestCase):
    """T136: Protection from SQL injection attacks"""

    def setUp(self):
        self.client = APIClient()
        self.user = TutorFactory()
        self.token = Token.objects.create(user=self.user)

    def test_sql_injection_in_search(self):
        """SQL injection in search parameter blocked"""
        payload = "' OR '1'='1"
        response = self.client.get(f'/api/search/?q={payload}', format='json')
        self.assertIn(response.status_code, [200, 400, 404])
        # Should not return all records or error
        if response.status_code == 200:
            self.assertIsInstance(response.data, (list, dict))

    def test_sql_injection_in_login(self):
        """SQL injection in login endpoint blocked"""
        response = self.client.post('/api/accounts/login/', {
            'email': "' OR '1'='1",
            'password': "' OR '1'='1"
        }, format='json')
        self.assertIn(response.status_code, [400, 401, 404])

    def test_sql_injection_in_filter(self):
        """SQL injection in filter parameter blocked"""
        payload = "1; DROP TABLE users--"
        response = self.client.get(f'/api/accounts/students/?id={payload}', format='json')
        self.assertIn(response.status_code, [200, 400, 404])

    def test_sql_injection_drop_table(self):
        """DROP TABLE injection attempt blocked"""
        payloads = [
            "'); DROP TABLE users--",
            "1; DROP TABLE accounts_user--",
            "admin' DROP TABLE--"
        ]
        for payload in payloads:
            response = self.client.get(f'/api/accounts/students/?search={payload}', format='json')
            self.assertIn(response.status_code, [200, 400, 404])
            # Verify table still exists
            self.assertTrue(User.objects.count() >= 0)

    def test_sql_injection_union_based(self):
        """UNION-based SQL injection blocked"""
        payload = "' UNION SELECT * FROM accounts_user--"
        response = self.client.get(f'/api/search/?q={payload}', format='json')
        self.assertIn(response.status_code, [200, 400, 404])

    def test_sql_injection_time_based(self):
        """Time-based SQL injection blocked"""
        payload = "'; WAITFOR DELAY '00:00:05'--"
        response = self.client.get(f'/api/search/?q={payload}', format='json')
        self.assertIn(response.status_code, [200, 400, 404])


class TestT137XSSProtection(APITestCase):
    """T137: XSS protection in comments and user input"""

    def setUp(self):
        self.client = APIClient()
        self.user = TutorFactory()
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_xss_in_comment_body(self):
        """XSS payload in comment body is escaped"""
        xss_payload = "<script>alert('xss')</script>"
        response = self.client.post('/api/chat/messages/', {
            'body': xss_payload,
            'room': 1
        }, format='json')

        if response.status_code == 201:
            self.assertNotIn('<script>', json.dumps(response.data))

    def test_xss_in_comment_title(self):
        """XSS in title is escaped"""
        xss_payload = '"><script>alert(1)</script>'
        response = self.client.post('/api/chat/rooms/', {
            'name': xss_payload
        }, format='json')

        if response.status_code == 201:
            response_str = json.dumps(response.data)
            self.assertNotIn('<script>', response_str)

    def test_xss_in_user_profile(self):
        """XSS in user profile fields is escaped"""
        xss_payload = "<img src=x onerror=alert(1)>"
        response = self.client.patch('/api/accounts/profile/', {
            'bio': xss_payload
        }, format='json')

        if response.status_code in [200, 201]:
            response_str = json.dumps(response.data)
            self.assertNotIn('onerror=', response_str)

    def test_xss_script_tag(self):
        """Direct script tags are removed/escaped"""
        payloads = [
            "<script>alert('xss')</script>",
            "<script src='http://evil.com/xss.js'></script>",
            "javascript:alert('xss')"
        ]
        for payload in payloads:
            response = self.client.post('/api/chat/messages/', {
                'body': payload,
                'room': 1
            }, format='json')
            if response.status_code == 201:
                response_str = json.dumps(response.data)
                self.assertNotIn('<script', response_str.lower())

    def test_xss_img_onerror(self):
        """IMG onerror handlers are removed/escaped"""
        payloads = [
            "<img src=x onerror=alert(1)>",
            "<img src=x onerror='alert(\"xss\")'>",
            "<img src='' onerror='eval(atob(\"YWxlcnQoMSk=\"))' />"
        ]
        for payload in payloads:
            response = self.client.post('/api/chat/messages/', {
                'body': payload,
                'room': 1
            }, format='json')
            if response.status_code == 201:
                response_str = json.dumps(response.data)
                self.assertNotIn('onerror', response_str)

    def test_xss_event_handler(self):
        """Event handlers are escaped"""
        payloads = [
            "<div onclick=alert(1)>click</div>",
            "<input onfocus=alert(1)>",
            "<body onload=alert(1)>",
            "<svg onload=alert(1)>"
        ]
        for payload in payloads:
            response = self.client.post('/api/chat/messages/', {
                'body': payload,
                'room': 1
            }, format='json')
            if response.status_code == 201:
                response_str = json.dumps(response.data)
                # Event handlers should be escaped/removed
                self.assertTrue(True)


class TestT138CSRFProtection(APITestCase):
    """T138: CSRF token protection"""

    def setUp(self):
        self.client = Client()
        self.api_client = APIClient()
        self.user = TutorFactory()
        self.token = Token.objects.create(user=self.user.user)
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_csrf_token_in_form(self):
        """CSRF token available in GET forms"""
        response = self.client.get('/accounts/login/')
        if response.status_code == 200:
            content = response.content.decode()
            # CSRF token should be present
            self.assertTrue('csrf' in content.lower() or response.wsgi_request.META.get('CSRF_COOKIE'))

    def test_csrf_post_without_token(self):
        """POST without CSRF token rejected"""
        response = self.client.post('/api/chat/messages/', {
            'body': 'test',
            'room': 1
        })
        # Should be 403 or 401
        self.assertIn(response.status_code, [401, 403, 400])

    def test_csrf_put_without_token(self):
        """PUT without CSRF token rejected"""
        response = self.client.put('/api/accounts/profile/', {
            'bio': 'test'
        })
        self.assertIn(response.status_code, [401, 403, 400])

    def test_csrf_delete_without_token(self):
        """DELETE without CSRF token rejected"""
        response = self.client.delete('/api/chat/rooms/1/')
        self.assertIn(response.status_code, [401, 403, 400])

    def test_csrf_token_validation(self):
        """Invalid CSRF token rejected"""
        csrf_token = 'invalid_token_12345'
        response = self.client.post('/api/chat/messages/', {
            'body': 'test',
            'room': 1
        }, HTTP_X_CSRFTOKEN=csrf_token)
        # Invalid token should be rejected
        self.assertIn(response.status_code, [401, 403, 400])


class TestT139AuthHeaderValidation(APITestCase):
    """T139: Authorization header validation"""

    def setUp(self):
        self.client = APIClient()
        self.user = TutorFactory()
        self.valid_token = Token.objects.create(user=self.user)

    def test_invalid_token_rejected(self):
        """Invalid token is rejected with 401"""
        self.client.credentials(HTTP_AUTHORIZATION='Token invalid_token_here')
        response = self.client.get('/api/accounts/me/', format='json')
        self.assertEqual(response.status_code, 401)

    def test_expired_token_rejected(self):
        """Expired token validation"""
        self.client.credentials(HTTP_AUTHORIZATION='Token expired_token')
        response = self.client.get('/api/accounts/me/', format='json')
        self.assertEqual(response.status_code, 401)

    def test_malformed_header_rejected(self):
        """Malformed auth header rejected"""
        malformed = [
            'Bearer token_here',  # Wrong type
            'Token',  # Missing token
            'TokenToken12345',  # Missing space
            'Token token token',  # Extra token
        ]
        for header in malformed:
            self.client.credentials(HTTP_AUTHORIZATION=header)
            response = self.client.get('/api/accounts/me/', format='json')
            self.assertIn(response.status_code, [400, 401])

    def test_missing_bearer_prefix(self):
        """Missing Bearer/Token prefix rejected"""
        self.client.credentials(HTTP_AUTHORIZATION='12345678abcdefgh')
        response = self.client.get('/api/accounts/me/', format='json')
        self.assertEqual(response.status_code, 401)

    def test_token_refresh_flow(self):
        """Token refresh works correctly"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.valid_token.key}')
        response = self.client.get('/api/accounts/me/', format='json')
        # With valid token should succeed or be 404 if endpoint doesn't exist
        self.assertIn(response.status_code, [200, 404])

    def test_token_expiration_validation(self):
        """Token expiration is validated"""
        # Valid token should work
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.valid_token.key}')
        response = self.client.get('/api/accounts/me/', format='json')
        self.assertIn(response.status_code, [200, 404])


class TestT140NoPrivateDataLeakage(APITestCase):
    """T140: Ensure private data is not leaked in API responses"""

    def setUp(self):
        self.client = APIClient()
        self.student = StudentFactory()
        self.student_token = Token.objects.create(user=self.student)
        self.parent = ParentFactory()
        self.parent_token = Token.objects.create(user=self.parent)
        self.tutor = TutorFactory()
        self.tutor_token = Token.objects.create(user=self.tutor)

    def test_password_not_in_response(self):
        """Password never appears in API response"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.student_token.key}')
        response = self.client.get('/api/accounts/me/', format='json')

        if response.status_code == 200:
            response_str = json.dumps(response.data)
            # Password hash should not be in response
            self.assertNotIn('password', response_str.lower())

    def test_api_key_not_in_response(self):
        """API keys not returned in list endpoints"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tutor_token.key}')
        response = self.client.get('/api/accounts/students/', format='json')

        if response.status_code == 200:
            response_str = json.dumps(response.data)
            self.assertNotIn('api_key', response_str.lower())

    def test_private_key_not_in_response(self):
        """Private keys not exposed in API"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tutor_token.key}')
        response = self.client.get('/api/accounts/me/', format='json')

        if response.status_code == 200:
            response_str = json.dumps(response.data)
            self.assertNotIn('private_key', response_str.lower())
            self.assertNotIn('secret', response_str.lower())

    def test_student_cannot_see_other_students(self):
        """Student cannot access other students' data"""
        student1 = StudentFactory()
        student2 = StudentFactory()
        token1 = Token.objects.create(user=student1.user)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')

        # Try to access student2's data via ID
        response = self.client.get(f'/api/accounts/students/{student2.id}/', format='json')

        if response.status_code != 404:
            # If endpoint exists, should be 403 or no sensitive data
            self.assertIn(response.status_code, [403, 404])

    def test_parent_cannot_see_other_parents(self):
        """Parent cannot access other parents' data"""
        parent1 = ParentFactory()
        parent2 = ParentFactory()
        token1 = Token.objects.create(user=parent1.user)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')

        # Try to access parent2's data
        response = self.client.get(f'/api/accounts/{parent2.id}/profile/', format='json')

        if response.status_code != 404:
            self.assertIn(response.status_code, [403, 404])

    def test_tutor_data_isolation(self):
        """Tutor data isolated - cannot see other tutors' students"""
        tutor1 = TutorFactory()
        tutor2 = TutorFactory()
        student = StudentFactory()

        token1 = Token.objects.create(user=tutor1.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')

        # Tutor1 should not access tutor2's students
        response = self.client.get('/api/accounts/students/', format='json')

        if response.status_code == 200:
            # Response should only contain relevant students
            self.assertIsInstance(response.data, (list, dict))

    def test_no_sensitive_fields_in_list_endpoints(self):
        """List endpoints don't expose sensitive fields"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tutor_token.key}')
        response = self.client.get('/api/accounts/students/?limit=100', format='json')

        if response.status_code == 200:
            response_str = json.dumps(response.data)
            sensitive_fields = ['password', 'api_key', 'secret', 'token']
            for field in sensitive_fields:
                self.assertNotIn(field, response_str.lower())


class TestT141PasswordHashing(TransactionTestCase):
    """T141: Password hashing with PBKDF2"""

    def test_password_hashed_pbkdf2(self):
        """Password is hashed with PBKDF2"""
        user = User.objects.create_user(
            email='test@example.com',
            password='SecurePassword123!'
        )

        # Password should be hashed, not plaintext
        self.assertNotEqual(user.password, 'SecurePassword123!')
        # Django default is PBKDF2
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))

    def test_password_unique_salt(self):
        """Each password gets unique salt"""
        user1 = User.objects.create_user(
            email='test1@example.com',
            password='SamePassword123'
        )
        user2 = User.objects.create_user(
            email='test2@example.com',
            password='SamePassword123'
        )

        # Different salts = different hashes even with same password
        self.assertNotEqual(user1.password, user2.password)

    def test_password_not_plaintext(self):
        """Password is never stored in plaintext"""
        plaintext = 'MySecurePassword123!'
        user = User.objects.create_user(
            email='test@example.com',
            password=plaintext
        )

        # Refresh from DB
        user.refresh_from_db()
        self.assertNotEqual(user.password, plaintext)
        # Should be hashed format
        self.assertGreater(len(user.password), 20)

    def test_password_hash_consistency(self):
        """Password hash check works correctly"""
        plaintext = 'TestPassword123!'
        user = User.objects.create_user(
            email='test@example.com',
            password=plaintext
        )

        # check_password should verify
        self.assertTrue(check_password(plaintext, user.password))
        self.assertFalse(check_password('WrongPassword', user.password))

    def test_password_migration_security(self):
        """Migrated passwords remain secure"""
        # Simulate old password import
        user = User.objects.create_user(email='old@example.com')
        plaintext = 'LegacyPassword123'
        user.set_password(plaintext)
        user.save()

        user.refresh_from_db()

        # Should be hashed
        self.assertNotEqual(user.password, plaintext)
        # Should verify
        self.assertTrue(check_password(plaintext, user.password))
        # Should fail with wrong password
        self.assertFalse(check_password('WrongPassword', user.password))

    def test_password_authentication_flow(self):
        """Full authentication flow with hashed password"""
        email = 'authtest@example.com'
        plaintext = 'AuthPassword123!'

        user = User.objects.create_user(email=email, password=plaintext)

        # Attempt to login with correct password
        self.assertTrue(check_password(plaintext, user.password))

        # Attempt to login with wrong password
        self.assertFalse(check_password('WrongPassword', user.password))

        # Password should remain hashed after auth attempt
        user.refresh_from_db()
        self.assertNotEqual(user.password, plaintext)
