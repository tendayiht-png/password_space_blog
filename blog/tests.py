import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import DRAFT, PUBLISHED, Idea, Post, UserContactProfile


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


class IdeaPageTests(TestCase):
    def test_logged_in_user_ideas_only_show_in_my_ideas(self):
        user = User.objects.create_user(
            username='idea_owner',
            email='idea_owner@example.com',
            password='VeryStr0ng!Password2026',
        )
        other_user = User.objects.create_user(
            username='other_owner',
            email='other_owner@example.com',
            password='VeryStr0ng!Password2026',
        )
        own_idea = Idea.objects.create(
            owner=user,
            name='Idea Owner',
            email='idea_owner@example.com',
            title='My private idea',
            idea='Hide this from the community list when I am logged in.',
        )
        other_idea = Idea.objects.create(
            owner=other_user,
            name='Other Owner',
            email='other_owner@example.com',
            title='Community idea',
            idea='This should stay visible on the share ideas page.',
        )

        self.client.force_login(user)

        share_response = self.client.get('/ideas/')
        self.assertEqual(share_response.status_code, 200)
        self.assertContains(share_response, 'Share your idea with us')
        self.assertNotContains(share_response, own_idea.title)
        self.assertNotContains(share_response, other_idea.title)

        my_ideas_response = self.client.get('/ideas/my/')
        self.assertEqual(my_ideas_response.status_code, 200)
        self.assertContains(my_ideas_response, own_idea.title)
        self.assertNotContains(my_ideas_response, other_idea.title)

        home_response = self.client.get('/')
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, own_idea.title)
        self.assertContains(home_response, other_idea.title)

    def test_share_ideas_claims_matching_anonymous_submissions_for_logged_in_user(self):
        user = User.objects.create_user(
            username='claimed_owner',
            email='claimed_owner@example.com',
            password='VeryStr0ng!Password2026',
        )
        claimed_idea = Idea.objects.create(
            owner=None,
            name='Claimed Owner',
            email='claimed_owner@example.com',
            title='Claimed after login',
            idea='This should move into My Ideas after login.',
        )

        self.client.force_login(user)

        share_response = self.client.get('/ideas/')
        self.assertEqual(share_response.status_code, 200)
        self.assertNotContains(share_response, claimed_idea.title)

        home_response = self.client.get('/')
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, claimed_idea.title)

        claimed_idea.refresh_from_db()
        self.assertEqual(claimed_idea.owner, user)

        my_ideas_response = self.client.get('/ideas/my/')
        self.assertEqual(my_ideas_response.status_code, 200)
        self.assertContains(my_ideas_response, claimed_idea.title)

    def test_latest_blog_idea_preview_links_to_full_detail_page(self):
        idea = Idea.objects.create(
            owner=None,
            name='Cafe Owner',
            email='cafe-owner@example.com',
            title='',
            idea=(
                "I Almost Lost My Business at Starbucks (And Didn't Realize It Until I Got Home). "
                "I connected to public Wi-Fi and signed into multiple accounts without checking the network details. "
                "This final phrase should only appear on the detail page."
            ),
        )

        home_response = self.client.get('/')
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, reverse('idea_detail', args=[idea.id]))
        home_html = home_response.content.decode('utf-8')
        self.assertTrue(
            ('Read Full Idea' in home_html) or ('Read On' in home_html),
            'Expected a call-to-action link for the idea preview card.',
        )
        self.assertNotContains(home_response, 'This final phrase should only appear on the detail page.')

        detail_response = self.client.get(reverse('idea_detail', args=[idea.id]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'I Almost Lost My Business at Starbucks')
        self.assertContains(detail_response, 'This final phrase should only appear on the detail page.')


class PostPublishingAndEditorTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username='post_author',
            email='author@example.com',
            password='VeryStr0ng!Password2026',
        )
        self.staff_user = User.objects.create_user(
            username='staff_editor',
            email='staff@example.com',
            password='VeryStr0ng!Password2026',
            is_staff=True,
        )

    def test_home_only_lists_published_posts(self):
        Post.objects.create(
            title='Published article',
            slug='published-article',
            author=self.author,
            content='<p>Visible content</p>',
            status=PUBLISHED,
        )
        Post.objects.create(
            title='Draft article',
            slug='draft-article',
            author=self.author,
            content='<p>Hidden content</p>',
            status=DRAFT,
        )

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Published article')
        self.assertNotContains(response, 'Draft article')

    def test_non_staff_cannot_access_draft_detail(self):
        draft_post = Post.objects.create(
            title='Private draft',
            slug='private-draft',
            author=self.author,
            content='<p>Draft body</p>',
            status=DRAFT,
        )

        response = self.client.get(reverse('post_detail', args=[draft_post.slug]))

        self.assertEqual(response.status_code, 404)

    def test_staff_can_access_draft_detail(self):
        draft_post = Post.objects.create(
            title='Staff-visible draft',
            slug='staff-visible-draft',
            author=self.author,
            content='<p>Draft body</p>',
            status=DRAFT,
        )
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('post_detail', args=[draft_post.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Staff-visible draft')

    def test_post_sanitization_removes_script_tags(self):
        post = Post.objects.create(
            title='Sanitized article',
            slug='sanitized-article',
            author=self.author,
            content='<h1>Allowed</h1><script>alert("xss")</script><strong>Safe</strong>',
            status=PUBLISHED,
        )

        self.assertNotIn('<script', post.content.lower())
        self.assertIn('<h1>Allowed</h1>', post.content)
        self.assertIn('<strong>Safe</strong>', post.content)

    def test_staff_editor_creates_draft_post(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('post_editor_page'),
            {
                'title': 'Editor draft',
                'slug': '',
                'excerpt': 'Excerpt text',
                'content': '<p>Draft content</p><script>alert(1)</script>',
                'status': str(DRAFT),
            },
        )

        self.assertEqual(response.status_code, 302)
        created = Post.objects.get(title='Editor draft')
        self.assertEqual(created.status, DRAFT)
        self.assertEqual(created.author, self.staff_user)
        self.assertNotIn('<script', created.content.lower())

    def test_authenticated_non_staff_can_access_editor(self):
        self.client.force_login(self.author)

        response = self.client.get(reverse('post_editor_page'))

        self.assertEqual(response.status_code, 200)

    def test_authenticated_non_staff_can_create_draft_post(self):
        self.client.force_login(self.author)

        response = self.client.post(
            reverse('post_editor_page'),
            {
                'title': 'Author draft',
                'slug': '',
                'excerpt': 'Author excerpt',
                'content': '<p>Author draft content</p><script>alert(1)</script>',
                'status': str(DRAFT),
            },
        )

        self.assertEqual(response.status_code, 302)
        created = Post.objects.get(title='Author draft')
        self.assertEqual(created.status, DRAFT)
        self.assertEqual(created.author, self.author)
        self.assertNotIn('<script', created.content.lower())
