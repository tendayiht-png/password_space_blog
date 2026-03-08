import json

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView, TemplateView

from .models import Post


class PostList(ListView):
    model = Post
    template_name = 'index.html'
    context_object_name = 'post_list'
    queryset = Post.objects.all().order_by('-created_on')


class PostDetail(DetailView):
    model = Post
    template_name = 'post_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'


class HowToPageView(TemplateView):
    template_name = 'how_to_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'How to Set Up Two-Factor Authentication (2FA)'
        context['description'] = (
            'Step-by-step guide to enable 2FA on your accounts '
            'and protect them from unauthorized access.'
        )
        context['time_estimate'] = 'Estimated Time: 5-8 min'
        context['difficulty'] = 'Difficulty: Beginner'
        context['outcome'] = 'Outcome: Account protected'
        return context


class ChecklistPageView(TemplateView):
    template_name = 'checklist_page.html'


class RegisterPageView(TemplateView):
    template_name = 'register.html'


def _parse_request_payload(request):
    """Support both JSON and form-encoded POST bodies."""
    content_type = request.headers.get('Content-Type', '')
    if 'application/json' in content_type:
        try:
            return json.loads(request.body.decode('utf-8') or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return request.POST.dict()


def _registration_errors(username, password, confirm_password):
    errors = {}

    if not username:
        errors['username'] = ['Username is required.']
    elif User.objects.filter(username__iexact=username).exists():
        errors['username'] = ['This username is already taken.']

    if not password:
        errors['password'] = ['Password is required.']

    if not confirm_password:
        errors['confirm_password'] = ['Please confirm your password.']

    if password and confirm_password and password != confirm_password:
        errors['confirm_password'] = ['Passwords do not match.']

    if password:
        try:
            validate_password(password, user=User(username=username))
        except ValidationError as exc:
            errors['password'] = list(exc.messages)

    return errors


@require_http_methods(['GET', 'POST'])
def register_api(request):
    """
    GET /API/register?username=<name> checks username availability.
    POST /API/register creates a new user with hashed password.
    """
    if request.method == 'GET':
        username = request.GET.get('username', '').strip()
        if not username:
            return JsonResponse(
                {'available': False, 'message': 'Username is required.'},
                status=400,
            )

        exists = User.objects.filter(username__iexact=username).exists()
        return JsonResponse({'available': not exists, 'exists': exists})

    payload = _parse_request_payload(request)
    username = payload.get('username', '').strip()
    password = payload.get('password', '')
    confirm_password = payload.get('confirm_password', '')

    errors = _registration_errors(username, password, confirm_password)
    if errors:
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    user = User.objects.create_user(username=username, password=password)
    return JsonResponse(
        {
            'ok': True,
            'message': 'Registration successful.',
            'user': {'id': user.id, 'username': user.username},
        },
        status=201,
    )


