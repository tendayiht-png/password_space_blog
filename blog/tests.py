import json

from django.contrib.auth.models import User
from django.test import TestCase

from .models import UserContactProfile


class RegistrationApiTests(TestCase):
    def test_username_availability_endpoint(self):
        User.objects.create_user(username='existing_user', password='MyStr0ng!Pass2026')

        response = self.client.get('/API/register', {'username': 'existing_user'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['available'], False)
        self.assertEqual(response.json()['exists'], True)

    def test_email_availability_endpoint(self):
        User.objects.create_user(
            username='existing_user',
            email='existing@example.com',
            password='MyStr0ng!Pass2026',
        )

        response = self.client.get('/API/register', {'email': 'existing@example.com'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['available'], False)
        self.assertEqual(response.json()['exists'], True)

    def test_registration_rejects_duplicate_username(self):
        User.objects.create_user(
            username='Alice',
            email='alice@example.com',
            password='MyStr0ng!Pass2026',
        )

        response = self.client.post(
            '/API/register',
            data=json.dumps(
                {
                    'username': 'alice',
                    'email': 'alice2@example.com',
                    'telephone': '+447700900100',
                    'password': 'AnotherStr0ng!Pass2026',
                    'confirm_password': 'AnotherStr0ng!Pass2026',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.json()['errors'])

    def test_registration_rejects_duplicate_email(self):
        User.objects.create_user(
            username='first_user',
            email='duplicate@example.com',
            password='MyStr0ng!Pass2026',
        )

        response = self.client.post(
            '/API/register',
            data=json.dumps(
                {
                    'username': 'second_user',
                    'email': 'duplicate@example.com',
                    'telephone': '+447700900200',
                    'password': 'AnotherStr0ng!Pass2026',
                    'confirm_password': 'AnotherStr0ng!Pass2026',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json()['errors'])

    def test_registration_creates_user_with_hashed_password(self):
        password = 'VeryStr0ng!Password2026'
        response = self.client.post(
            '/API/register',
            data=json.dumps(
                {
                    'username': 'new_user',
                    'email': 'new_user@example.com',
                    'telephone': '+447700900300',
                    'password': password,
                    'confirm_password': password,
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        created = User.objects.get(username='new_user')
        self.assertNotEqual(created.password, password)
        self.assertIn('$', created.password)
        self.assertTrue(created.check_password(password))

        profile = UserContactProfile.objects.get(user=created)
        self.assertEqual(profile.telephone, '+447700900300')


class LoginApiTests(TestCase):
    def test_login_rejects_mismatched_telephone(self):
        user = User.objects.create_user(
            username='login_user',
            email='login_user@example.com',
            password='VeryStr0ng!Password2026',
        )
        UserContactProfile.objects.create(user=user, telephone='+447700900400')

        response = self.client.post(
            '/API/login',
            data=json.dumps(
                {
                    'username': 'login_user',
                    'email': 'login_user@example.com',
                    'telephone': '+447700900499',
                    'password': 'VeryStr0ng!Password2026',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['ok'], False)

    def test_login_succeeds_with_matching_username_email_and_telephone(self):
        user = User.objects.create_user(
            username='login_ok',
            email='login_ok@example.com',
            password='VeryStr0ng!Password2026',
        )
        UserContactProfile.objects.create(user=user, telephone='07700900500')

        response = self.client.post(
            '/API/login',
            data=json.dumps(
                {
                    'username': 'login_ok',
                    'email': 'login_ok@example.com',
                    'telephone': '07700 900500',
                    'password': 'VeryStr0ng!Password2026',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['ok'], True)
