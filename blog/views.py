import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView, TemplateView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Idea, Post


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


def _get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _idea_rate_limit_key(client_ip):
    return f'idea-submit:{client_ip}'


def _is_idea_rate_limited(client_ip):
    limit = int(getattr(settings, 'IDEA_SUBMISSION_LIMIT', 3))
    current_count = int(cache.get(_idea_rate_limit_key(client_ip), 0))
    return current_count >= limit


def _record_idea_submission(client_ip):
    key = _idea_rate_limit_key(client_ip)
    window_seconds = int(getattr(settings, 'IDEA_SUBMISSION_WINDOW_SECONDS', 3600))
    current_count = int(cache.get(key, 0)) + 1
    cache.set(key, current_count, timeout=window_seconds)


def _idea_notification_recipients():
    recipients = list(getattr(settings, 'IDEA_NOTIFICATION_RECIPIENTS', []))
    if recipients:
        return recipients
    return [email for _, email in getattr(settings, 'ADMINS', []) if email]


def _send_idea_notification_email(idea_obj):
    recipients = _idea_notification_recipients()
    if not recipients:
        return

    subject = f"New idea submitted: {idea_obj.title or 'Untitled idea'}"
    message = (
        f"A new idea was submitted on Password Safe Blog.\n\n"
        f"Name: {idea_obj.name}\n"
        f"Email: {idea_obj.email}\n"
        f"Title: {idea_obj.title or 'Untitled'}\n"
        f"Submitted: {idea_obj.created_on}\n\n"
        f"Idea:\n{idea_obj.idea}\n"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@passwordspaceblog.com'),
        recipient_list=recipients,
        fail_silently=True,
    )


def _send_idea_confirmation_email(idea_obj):
    if not idea_obj.email:
        return

    subject = 'Thanks for sharing your idea with Password Safe Blog'
    message = (
        f"Hi {idea_obj.name},\n\n"
        "Thanks for sending your idea. Our team has received it and will review it for future content.\n\n"
        "Best regards,\n"
        "Password Safe Blog Team"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@passwordspaceblog.com'),
        recipient_list=[idea_obj.email],
        fail_silently=True,
    )


def ideas_page(request):
    """Render and handle the user ideas submission form."""
    form_data = {
        'name': '',
        'email': '',
        'title': '',
        'idea': '',
    }
    errors = {}
    success_message = ''

    if request.method == 'POST':
        # Hidden honeypot field catches basic form bots.
        if request.POST.get('website', '').strip():
            success_message = 'Thank you, your idea has been submitted.'
            return render(
                request,
                'ideas.html',
                {
                    'form_data': form_data,
                    'errors': errors,
                    'success_message': success_message,
                },
            )

        client_ip = _get_client_ip(request)
        form_data = {
            'name': request.POST.get('name', '').strip(),
            'email': request.POST.get('email', '').strip(),
            'title': request.POST.get('title', '').strip(),
            'idea': request.POST.get('idea', '').strip(),
        }

        if not form_data['name']:
            errors['name'] = 'Please enter your name.'
        if not form_data['email']:
            errors['email'] = 'Please enter your email.'
        elif form_data['email']:
            try:
                validate_email(form_data['email'])
            except ValidationError:
                errors['email'] = 'Please enter a valid email address.'
        if not form_data['idea']:
            errors['idea'] = 'Please share your idea.'

        if _is_idea_rate_limited(client_ip):
            errors['non_field'] = 'Too many submissions from this connection. Please try again in about an hour.'

        if not errors:
            idea_obj = Idea.objects.create(
                name=form_data['name'],
                email=form_data['email'],
                title=form_data['title'],
                idea=form_data['idea'],
            )
            _record_idea_submission(client_ip)
            _send_idea_notification_email(idea_obj)
            _send_idea_confirmation_email(idea_obj)
            success_message = 'Thank you, your idea has been submitted.'
            form_data = {
                'name': '',
                'email': '',
                'title': '',
                'idea': '',
            }

    return render(
        request,
        'ideas.html',
        {
            'form_data': form_data,
            'errors': errors,
            'success_message': success_message,
        },
    )


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


class SettingsPageView(LoginRequiredMixin, TemplateView):
    """User account settings page with account deletion option."""
    template_name = 'settings.html'
    login_url = '/register/'


@login_required(login_url='/register/')
@require_http_methods(['DELETE'])
def delete_account_api(request):
    """
    DELETE /API/delete-account permanently deletes the user account
    and all associated data after password verification.
    """
    try:
        payload = _parse_request_payload(request)
        password = payload.get('password', '')

        if not password:
            return JsonResponse(
                {'ok': False, 'message': 'Password is required.'},
                status=400,
            )

        # Verify password
        user = authenticate(username=request.user.username, password=password)
        if user is None:
            return JsonResponse(
                {'ok': False, 'message': 'Incorrect password. Please try again.'},
                status=403,
            )

        # Store user info for email before deletion
        username = user.username
        email = user.email or ''
        user_id = user.id

        # Perform cascading delete in a transaction
        with transaction.atomic():
            # Django's ORM handles cascading deletes automatically
            # This will delete all related objects (blog_posts, comments, etc.)
            user.delete()

        # Log out the user
        logout(request)

        # Send farewell email if email is set
        if email:
            _send_account_deletion_email(username, email)

        return JsonResponse(
            {
                'ok': True,
                'message': 'Your account has been permanently deleted. We\'re sorry to see you go.',
                'user_id': user_id,
            },
            status=200,
        )

    except Exception as e:
        return JsonResponse(
            {'ok': False, 'message': 'An error occurred during account deletion.'},
            status=500,
        )


def _send_account_deletion_email(username, email):
    """Send a farewell email after account deletion."""
    try:
        subject = 'Your Password Space Blog Account Has Been Deleted'
        message = f"""
Hello {username},

This email confirms that your Password Space Blog account has been permanently deleted.

All your data, including:
- Your user profile
- Blog posts and comments
- Account activity history

...has been removed from our servers.

If you deleted your account by mistake or have any concerns, please contact our support team as soon as possible.

We're sorry to see you go. If you ever want to return, you're always welcome to create a new account.

Best regards,
The Password Space Blog Team
        """

        send_mail(
            subject=subject,
            message=message.strip(),
            from_email='noreply@passwordspaceblog.com',
            recipient_list=[email],
            fail_silently=True,  # Don't fail the deletion if email fails
        )
    except Exception:
        # Log error but don't fail the deletion
        pass


class ForgotPasswordView(TemplateView):
    """Password reset request page."""
    template_name = 'forgot_password.html'


class ResetPasswordView(TemplateView):
    """Password reset confirmation page with token."""
    template_name = 'reset_password.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['uidb64'] = kwargs.get('uidb64', '')
        context['token'] = kwargs.get('token', '')
        return context


@require_http_methods(['POST'])
def password_reset_request_api(request):
    """
    POST /API/password-reset-request - Request password reset.
    
    Uses a generic message to prevent username enumeration attacks.
    Always returns success message regardless of whether user exists.
    """
    try:
        payload = _parse_request_payload(request)
        identifier = payload.get('identifier', '').strip()

        if not identifier:
            # Still return generic message
            return JsonResponse(
                {
                    'ok': True,
                    'message': 'If an account with that username or email exists, a password reset link has been sent.',
                },
                status=200,
            )

        # Try to find user by username or email
        user = None
        try:
            # First try username (case-insensitive)
            user = User.objects.filter(username__iexact=identifier).first()
            if not user:
                # Then try email
                user = User.objects.filter(email__iexact=identifier).first()
        except Exception:
            pass

        # If user exists and has email, send reset link
        if user and user.email:
            token = default_token_generator.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build reset URL
            reset_url = f"{request.scheme}://{request.get_host()}/reset-password/{uidb64}/{token}/"
            
            _send_password_reset_email(user.username, user.email, reset_url)

        # ALWAYS return generic success message (anti-enumeration)
        return JsonResponse(
            {
                'ok': True,
                'message': 'If an account with that username or email exists, a password reset link has been sent.',
            },
            status=200,
        )

    except Exception:
        # Even on error, return generic message
        return JsonResponse(
            {
                'ok': True,
                'message': 'If an account with that username or email exists, a password reset link has been sent.',
            },
            status=200,
        )


@require_http_methods(['POST'])
def password_reset_confirm_api(request):
    """
    POST /API/password-reset-confirm - Confirm password reset with token.
    
    Validates the token and sets the new password.
    """
    try:
        payload = _parse_request_payload(request)
        uidb64 = payload.get('uidb64', '')
        token = payload.get('token', '')
        password = payload.get('password', '')
        confirm_password = payload.get('confirm_password', '')

        if not all([uidb64, token, password, confirm_password]):
            return JsonResponse(
                {'ok': False, 'message': 'All fields are required.'},
                status=400,
            )

        if password != confirm_password:
            return JsonResponse(
                {'ok': False, 'message': 'Passwords do not match.'},
                status=400,
            )

        # Decode user ID
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return JsonResponse(
                {'ok': False, 'message': 'Invalid reset link.'},
                status=400,
            )

        # Validate token
        if not default_token_generator.check_token(user, token):
            return JsonResponse(
                {'ok': False, 'message': 'This password reset link has expired or is invalid.'},
                status=400,
            )

        # Validate password strength
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            return JsonResponse(
                {'ok': False, 'message': ' '.join(exc.messages)},
                status=400,
            )

        # Set new password
        user.set_password(password)
        user.save()

        return JsonResponse(
            {
                'ok': True,
                'message': 'Your password has been reset successfully. You can now log in with your new password.',
            },
            status=200,
        )

    except Exception:
        return JsonResponse(
            {'ok': False, 'message': 'An error occurred. Please try again.'},
            status=500,
        )


def _send_password_reset_email(username, email, reset_url):
    """Send password reset email with reset link."""
    try:
        subject = 'Password Reset Request - Password Space Blog'
        message = f"""
Hello {username},

You recently requested to reset your password for your Password Space Blog account.

Click the link below to reset your password:

{reset_url}

This link will expire in 24 hours for security reasons.

If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.

For security tips and best practices, visit our blog at Password Space Blog.

Best regards,
The Password Space Blog Team
        """

        send_mail(
            subject=subject,
            message=message.strip(),
            from_email='noreply@passwordspaceblog.com',
            recipient_list=[email],
            fail_silently=True,
        )
    except Exception:
        # Log error but don't fail the request
        pass


# ============================================================================
# JWT Authentication Views
# ============================================================================


def _jwt_config(key, default):
    return getattr(settings, 'SIMPLE_JWT', {}).get(key, default)


def _jwt_cookie_secure(request):
    # Use secure cookies in production and when request already uses HTTPS.
    return bool(_jwt_config('AUTH_COOKIE_SECURE', False) or request.is_secure())


def _token_max_age_seconds(token_obj):
    exp = int(token_obj.get('exp', 0))
    now = int(timezone.now().timestamp())
    return max(exp - now, 0)


def _set_auth_cookie(response, key, value, max_age, request):
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        httponly=_jwt_config('AUTH_COOKIE_HTTP_ONLY', True),
        secure=_jwt_cookie_secure(request),
        samesite=_jwt_config('AUTH_COOKIE_SAMESITE', 'Lax'),
        path='/',
    )


def _delete_auth_cookie(response, key, request):
    response.delete_cookie(
        key,
        path='/',
        samesite=_jwt_config('AUTH_COOKIE_SAMESITE', 'Lax'),
    )

class LoginPageView(TemplateView):
    """Login page for JWT authentication."""
    template_name = 'login.html'


@require_http_methods(['POST'])
def login_api(request):
    """
    POST /API/login - Authenticate user and set JWT cookies.

    Tokens are stored only in HTTP-only cookies (not response JSON).
    """
    try:
        payload = _parse_request_payload(request)
        username = payload.get('username', '').strip()
        password = payload.get('password', '')
        remember_me = payload.get('remember_me', False)

        if isinstance(remember_me, str):
            remember_me = remember_me.strip().lower() in {'1', 'true', 'yes', 'on'}

        if not username or not password:
            return JsonResponse(
                {'ok': False, 'message': 'Username and password are required.'},
                status=400,
            )

        # Authenticate user
        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse(
                {'ok': False, 'message': 'Invalid username or password.'},
                status=401,
            )

        # Log in the user (creates session)
        login(request, user)

        # Generate JWT tokens
        refresh_obj = RefreshToken.for_user(user)
        if remember_me:
            refresh_obj.set_exp(lifetime=timedelta(days=30))

        access_obj = refresh_obj.access_token
        access_token = str(access_obj)
        refresh_token = str(refresh_obj)

        access_cookie_name = _jwt_config('AUTH_COOKIE', 'access_token')
        refresh_cookie_name = _jwt_config('AUTH_COOKIE_REFRESH', 'refresh_token')

        # Prepare response
        response_data = {
            'ok': True,
            'message': 'Login successful.',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'redirect': '/settings/',
        }

        response = JsonResponse(response_data, status=200)

        _set_auth_cookie(
            response,
            access_cookie_name,
            access_token,
            _token_max_age_seconds(access_obj),
            request,
        )

        _set_auth_cookie(
            response,
            refresh_cookie_name,
            refresh_token,
            _token_max_age_seconds(refresh_obj),
            request,
        )

        return response

    except Exception:
        return JsonResponse(
            {'ok': False, 'message': 'An error occurred during login.'},
            status=500,
        )


@require_http_methods(['POST'])
def refresh_token_api(request):
    """
    POST /API/token/refresh - Refresh access token using refresh token.

    Reads the refresh token from HTTP-only cookie and rotates it.
    """
    try:
        refresh_cookie_name = _jwt_config('AUTH_COOKIE_REFRESH', 'refresh_token')
        access_cookie_name = _jwt_config('AUTH_COOKIE', 'access_token')

        # Get refresh token from cookie
        refresh_token = request.COOKIES.get(refresh_cookie_name)

        if not refresh_token:
            return JsonResponse(
                {'ok': False, 'message': 'Refresh token not found.'},
                status=401,
            )

        rotate_refresh_tokens = bool(_jwt_config('ROTATE_REFRESH_TOKENS', True))
        blacklist_after_rotation = bool(_jwt_config('BLACKLIST_AFTER_ROTATION', True))

        # Validate and refresh token
        try:
            incoming_refresh = RefreshToken(refresh_token)

            user_id = incoming_refresh.get('user_id')
            user = User.objects.filter(pk=user_id, is_active=True).first()
            if user is None:
                return JsonResponse(
                    {'ok': False, 'message': 'Invalid or expired refresh token.'},
                    status=401,
                )

            refresh_obj = incoming_refresh
            if rotate_refresh_tokens:
                refresh_obj = RefreshToken.for_user(user)

                default_refresh_seconds = int(
                    _jwt_config('REFRESH_TOKEN_LIFETIME', timedelta(days=7)).total_seconds()
                )
                incoming_seconds = _token_max_age_seconds(incoming_refresh)
                if incoming_seconds > default_refresh_seconds + 60:
                    refresh_obj.set_exp(lifetime=timedelta(days=30))

                if blacklist_after_rotation:
                    try:
                        incoming_refresh.blacklist()
                    except Exception:
                        pass

            access_obj = refresh_obj.access_token
            access_token = str(access_obj)
        except Exception:
            return JsonResponse(
                {'ok': False, 'message': 'Invalid or expired refresh token.'},
                status=401,
            )

        # Prepare response
        response_data = {
            'ok': True,
            'message': 'Token refreshed successfully.',
        }

        response = JsonResponse(response_data, status=200)

        _set_auth_cookie(
            response,
            access_cookie_name,
            access_token,
            _token_max_age_seconds(access_obj),
            request,
        )

        if rotate_refresh_tokens:
            _set_auth_cookie(
                response,
                refresh_cookie_name,
                str(refresh_obj),
                _token_max_age_seconds(refresh_obj),
                request,
            )

        return response

    except Exception:
        return JsonResponse(
            {'ok': False, 'message': 'An error occurred during token refresh.'},
            status=500,
        )


@require_http_methods(['POST'])
def logout_api(request):
    """
    POST /API/logout - Log out user and clear JWT tokens.
    
    Blacklists the refresh token (if configured) and clears cookies.
    """
    try:
        refresh_cookie_name = _jwt_config('AUTH_COOKIE_REFRESH', 'refresh_token')
        access_cookie_name = _jwt_config('AUTH_COOKIE', 'access_token')

        # Get refresh token from cookie
        refresh_token = request.COOKIES.get(refresh_cookie_name)

        # Blacklist the refresh token if available
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()  # Requires token blacklist app
            except Exception:
                # If blacklist not configured, just clear cookies
                pass

        # Log out Django session
        logout(request)

        response_data = {
            'ok': True,
            'message': 'Logged out successfully.',
            'redirect': '/',
        }

        response = JsonResponse(response_data, status=200)

        # Delete JWT cookies
        _delete_auth_cookie(response, access_cookie_name, request)
        _delete_auth_cookie(response, refresh_cookie_name, request)

        return response

    except Exception:
        return JsonResponse(
            {'ok': False, 'message': 'An error occurred during logout.'},
            status=500,
        )
