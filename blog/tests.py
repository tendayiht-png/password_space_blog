import json

from django.contrib.auth.models import User
from django.test import TestCase


class RegistrationApiTests(TestCase):
    def test_username_availability_endpoint(self):
        User.objects.create_user(username='existing_user', password='MyStr0ng!Pass2026')

        response = self.client.get('/API/register', {'username': 'existing_user'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['available'], False)
        self.assertEqual(response.json()['exists'], True)

    def test_registration_rejects_duplicate_username(self):
        User.objects.create_user(username='Alice', password='MyStr0ng!Pass2026')

        response = self.client.post(
            '/API/register',
            data=json.dumps(
                {
                    'username': 'alice',
                    'password': 'AnotherStr0ng!Pass2026',
                    'confirm_password': 'AnotherStr0ng!Pass2026',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.json()['errors'])

    def test_registration_creates_user_with_hashed_password(self):
        password = 'VeryStr0ng!Password2026'
        response = self.client.post(
            '/API/register',
            data=json.dumps(
                {
                    'username': 'new_user',
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
