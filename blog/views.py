import json
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
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
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView, TemplateView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Idea, Post, UserContactProfile


class PostList(ListView):
    model = Post
    template_name = 'index.html'
    context_object_name = 'post_list'
    queryset = Post.objects.all().order_by('-created_on')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_ideas'] = Idea.objects.select_related('owner').order_by('-created_on')[:6]
        return context


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


def _account_contact_email(user):
    """Return best available account email identity for ownership linking."""
    if not user or not user.is_authenticated:
        return ''

    account_email = (user.email or '').strip()
    if account_email:
        return account_email

    username = (user.username or '').strip()
    if '@' in username:
        return username

    return ''


def _claim_unowned_ideas_for_user(user):
    """Attach previously anonymous ideas to the authenticated account when possible."""
    contact_email = _account_contact_email(user)
    if not contact_email:
        return 0

    return Idea.objects.filter(owner__isnull=True, email__iexact=contact_email).update(owner=user)


@login_required(login_url='/login/')
def my_ideas_page(request):
    from datetime import datetime, timedelta
    from django.db.models import Q

    _claim_unowned_ideas_for_user(request.user)

    ideas = Idea.objects.filter(owner=request.user).order_by('-created_on')
    
    # Get filter parameters
    filter_type = request.GET.get('filter', 'all')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Apply preset filters
    today = datetime.now()
    if filter_type == 'this_week':
        start_date = today - timedelta(days=today.weekday())
        ideas = ideas.filter(created_on__gte=start_date)
    elif filter_type == 'this_month':
        start_date = today.replace(day=1)
        ideas = ideas.filter(created_on__gte=start_date)
    elif filter_type == 'this_year':
        start_date = today.replace(month=1, day=1)
        ideas = ideas.filter(created_on__gte=start_date)
    elif filter_type == 'custom':
        # Custom date range filtering
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                ideas = ideas.filter(created_on__gte=from_date)
            except ValueError:
                pass
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d')
                to_date = to_date.replace(hour=23, minute=59, second=59)
                ideas = ideas.filter(created_on__lte=to_date)
            except ValueError:
                pass
    
    return render(request, 'my_ideas.html', {
        'ideas': ideas,
        'filter_type': filter_type,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required(login_url='/login/')
def unallocated_ideas_page(request):
    """Admin-only folder for ideas that no longer have an account owner."""
    if not request.user.is_staff:
        messages.error(request, 'Only admin users can access the Unallocated Ideas folder.')
        return redirect('home')

    ideas = Idea.objects.filter(owner__isnull=True).order_by('-created_on')
    return render(request, 'unallocated_ideas.html', {'ideas': ideas})


@login_required(login_url='/login/')
@require_http_methods(['GET', 'POST'])
def edit_idea_page(request, idea_id):
    idea_obj = get_object_or_404(Idea, pk=idea_id, owner=request.user)
    errors = {}
    form_data = {
        'title': idea_obj.title,
        'idea': idea_obj.idea,
    }

    if request.method == 'POST':
        form_data = {
            'title': request.POST.get('title', '').strip(),
            'idea': request.POST.get('idea', '').strip(),
        }

        if not form_data['idea']:
            errors['idea'] = 'Idea content cannot be empty.'

        if not errors:
            idea_obj.title = form_data['title']
            idea_obj.idea = form_data['idea']
            idea_obj.save(update_fields=['title', 'idea'])
            messages.success(request, 'Your idea was updated successfully.')
            return redirect('my_ideas_page')

    return render(
        request,
        'idea_edit.html',
        {
            'idea_obj': idea_obj,
            'form_data': form_data,
            'errors': errors,
        },
    )


@login_required(login_url='/login/')
@require_http_methods(['POST'])
def delete_idea(request, idea_id):
    idea_obj = get_object_or_404(Idea, pk=idea_id, owner=request.user)
    idea_obj.delete()
    messages.success(request, 'Your idea was deleted successfully.')
    return redirect('my_ideas_page')


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
    admin_email = getattr(settings, 'ADMIN_EMAIL', '').strip()
    if admin_email:
        return [admin_email]
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


def _move_user_ideas_to_unallocated(user):
    """Keep idea records after account deletion while removing account ownership."""
    if not user:
        return 0

    return Idea.objects.filter(owner=user).update(
        owner=None,
        name='Deleted User',
        email=f'deleted-user-{user.id}@passwordspaceblog.invalid',
    )


def ideas_page(request):
    """Render and handle the user ideas submission form."""
    form_data = {
        'name': request.user.get_full_name() or request.user.username if request.user.is_authenticated else '',
        'email': request.user.email if request.user.is_authenticated else '',
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
                owner=request.user if request.user.is_authenticated else None,
                name=form_data['name'],
                email=form_data['email'],
                title=form_data['title'],
                idea=form_data['idea'],
            )
            _record_idea_submission(client_ip)
            _send_idea_notification_email(idea_obj)
            _send_idea_confirmation_email(idea_obj)
            messages.success(request, 'Thank you, your idea has been submitted.')
            return redirect('ideas_page')

    return render(
        request,
        'ideas.html',
        {
            'form_data': form_data,
            'errors': errors,
            'success_message': success_message,
            'community_ideas': Idea.objects.select_related('owner').order_by('-created_on'),
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


def _normalized_email(value):
    return (value or '').strip().lower()


def _normalize_telephone(value):
    raw = (value or '').strip()
    if not raw:
        return ''

    digits = ''.join(ch for ch in raw if ch.isdigit())
    if not digits:
        return ''

    return f'+{digits}' if raw.startswith('+') else digits


def _looks_like_valid_telephone(value):
    normalized = _normalize_telephone(value)
    if not normalized:
        return False

    digit_count = len(normalized.lstrip('+'))
    return 7 <= digit_count <= 15


def _registration_errors(username, email, telephone, password, confirm_password):
    errors = {}

    if not username:
        errors['username'] = ['Username is required.']
    elif User.objects.filter(username__iexact=username).exists():
        errors['username'] = ['This username is already taken.']

    if not email:
        errors['email'] = ['Email is required.']
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = ['Please enter a valid email address.']
        else:
            if User.objects.filter(email__iexact=email).exists():
                errors['email'] = ['This email is already registered.']

    if not telephone:
        errors['telephone'] = ['Telephone is required.']
    elif not _looks_like_valid_telephone(telephone):
        errors['telephone'] = ['Please enter a valid telephone number (7 to 15 digits).']

    if not password:
        errors['password'] = ['Password is required.']

    if not confirm_password:
        errors['confirm_password'] = ['Please confirm your password.']

    if password and confirm_password and password != confirm_password:
        errors['confirm_password'] = ['Passwords do not match.']

    if password:
        try:
            validate_password(password, user=User(username=username, email=email))
        except ValidationError as exc:
            errors['password'] = list(exc.messages)

    return errors


@require_http_methods(['GET', 'POST'])
def register_api(request):
    """
    GET /API/register?username=<name> or ?email=<email> checks availability.
    POST /API/register creates a new user with hashed password.
    """
    if request.method == 'GET':
        username = request.GET.get('username', '').strip()
        email = request.GET.get('email', '').strip()

        if username:
            exists = User.objects.filter(username__iexact=username).exists()
            return JsonResponse({'available': not exists, 'exists': exists, 'field': 'username'})

        if email:
            try:
                validate_email(email)
            except ValidationError:
                return JsonResponse(
                    {'available': False, 'message': 'Please enter a valid email address.'},
                    status=400,
                )

            exists = User.objects.filter(email__iexact=email).exists()
            return JsonResponse({'available': not exists, 'exists': exists, 'field': 'email'})

        return JsonResponse(
            {'available': False, 'message': 'Username or email is required.'},
            status=400,
        )

    payload = _parse_request_payload(request)
    username = payload.get('username', '').strip()
    email = payload.get('email', '').strip()
    telephone = payload.get('telephone', '').strip()
    password = payload.get('password', '')
    confirm_password = payload.get('confirm_password', '')

    errors = _registration_errors(username, email, telephone, password, confirm_password)
    if errors:
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )
    UserContactProfile.objects.update_or_create(
        user=user,
        defaults={'telephone': _normalize_telephone(telephone)},
    )

    return JsonResponse(
        {
            'ok': True,
            'message': 'Registration successful.',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
        },
        status=201,
    )


class SettingsPageView(LoginRequiredMixin, TemplateView):
    """User account settings page with account deletion option."""
    template_name = 'settings.html'
    login_url = '/register/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        display_email = (self.request.user.email or '').strip()

        # Backward compatibility for accounts created when email was stored in username.
        if not display_email and '@' in self.request.user.username:
            display_email = self.request.user.username

        context['display_email'] = display_email
        return context


@login_required(login_url='/register/')
@require_http_methods(['DELETE'])
def delete_account_api(request):
    """
    DELETE /API/delete-account permanently deletes the user account
    after password verification.

    Ideas submitted by the user are retained anonymously and moved into
    the Unallocated Ideas folder for admin review.
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
        moved_ideas = 0

        # Perform account cleanup in a transaction
        with transaction.atomic():
            moved_ideas = _move_user_ideas_to_unallocated(user)
            user.delete()

        # Log out the user
        logout(request)

        # Send farewell email if email is set
        if email:
            _send_account_deletion_email(username, email, moved_ideas)

        success_message = 'Your account has been permanently deleted. We\'re sorry to see you go.'
        if moved_ideas:
            success_message += ' Your submitted ideas were kept anonymously in the Unallocated Ideas folder.'

        return JsonResponse(
            {
                'ok': True,
                'message': success_message,
                'user_id': user_id,
                'unallocated_ideas_count': moved_ideas,
            },
            status=200,
        )

    except Exception as e:
        return JsonResponse(
            {'ok': False, 'message': 'An error occurred during account deletion.'},
            status=500,
        )


def _send_account_deletion_email(username, email, moved_ideas=0):
    """Send a farewell email after account deletion."""
    try:
        subject = 'Your Password Space Blog Account Has Been Deleted'
        ideas_message = ''
        if moved_ideas:
            ideas_message = (
                f"\nYour {moved_ideas} submitted idea(s) were retained without account ownership "
                "for editorial review in our unallocated folder."
            )

        message = f"""
Hello {username},

This email confirms that your Password Space Blog account has been permanently deleted.

All your data, including:
- Your user profile
- Account access and credentials
- Account activity history

...has been removed from our servers.
{ideas_message}

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
        email = payload.get('email', '').strip()
        telephone = payload.get('telephone', '').strip()
        password = payload.get('password', '')
        remember_me = payload.get('remember_me', False)

        if isinstance(remember_me, str):
            remember_me = remember_me.strip().lower() in {'1', 'true', 'yes', 'on'}

        if not username or not email or not telephone or not password:
            return JsonResponse(
                {'ok': False, 'message': 'Username, email, telephone, and password are required.'},
                status=400,
            )

        if not _looks_like_valid_telephone(telephone):
            return JsonResponse(
                {
                    'ok': False,
                    'message': 'Please enter a valid telephone number (7 to 15 digits).',
                },
                status=400,
            )

        # Validate account identity before password check.
        user = User.objects.filter(username__iexact=username).first()
        if user is None:
            return JsonResponse(
                {'ok': False, 'message': 'Invalid username, email, telephone, or password.'},
                status=401,
            )

        if _normalized_email(_account_contact_email(user)) != _normalized_email(email):
            return JsonResponse(
                {'ok': False, 'message': 'Invalid username, email, telephone, or password.'},
                status=401,
            )

        normalized_telephone = _normalize_telephone(telephone)
        profile, _ = UserContactProfile.objects.get_or_create(user=user)
        stored_telephone = _normalize_telephone(profile.telephone)

        if stored_telephone and stored_telephone != normalized_telephone:
            return JsonResponse(
                {'ok': False, 'message': 'Invalid username, email, telephone, or password.'},
                status=401,
            )

        if not stored_telephone:
            profile.telephone = normalized_telephone
            profile.save(update_fields=['telephone'])

        # Authenticate user
        authenticated_user = authenticate(request, username=user.username, password=password)
        if authenticated_user is None:
            return JsonResponse(
                {'ok': False, 'message': 'Invalid username, email, telephone, or password.'},
                status=401,
            )

        # Log in the user (creates session)
        login(request, authenticated_user)

        claimed_ideas = _claim_unowned_ideas_for_user(authenticated_user)

        # Generate JWT tokens
        refresh_obj = RefreshToken.for_user(authenticated_user)
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
                'id': authenticated_user.id,
                'username': authenticated_user.username,
                'email': authenticated_user.email,
            },
            'claimed_ideas': claimed_ideas,
            'redirect': '/ideas/my/',
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
