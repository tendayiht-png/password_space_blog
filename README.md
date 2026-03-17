# Password Space Blog

Password Space Blog is a Django 4.2 web application focused on practical cybersecurity guidance, especially password hygiene and account protection. It combines educational articles with a community idea pipeline where visitors can submit stories and suggestions for future content.

## Product Overview

The platform includes:

- Security article publishing with excerpt cards and full detail pages.
- A merged home/about experience with latest content and mission messaging.
- Community idea submission and a user-owned idea management area.
- Secure account flows: register, login, logout, account settings, and password reset.
- Security controls around submissions and authentication.

## Core Features

- Home page with latest articles and latest blog ideas.
- About section with motion background and clear product mission.
- Full post pages via slug routes.
- 2FA how-to page.
- Share Ideas form for visitors and authenticated users.
- My Ideas area (auth required) for viewing, filtering, editing, and deleting owned ideas.
- Idea detail page for full idea text, with home cards showing preview text and a click-through link.
- Admin-only unallocated ideas view for records that no longer have an owner.

## User Stories

### User Stories

- As a user, I want to read recent cybersecurity articles from the home page so that I can improve my online safety quickly.
- As a user, I want to open full article pages so that I can read complete guidance and examples.
- As a user, I want to view a 2FA setup guide so that I can secure my most important accounts.
- As a user, I want to submit an idea from the Share Ideas page so that I can influence future blog topics.
- As a user, I want long ideas previewed in a shortened format on the home page so that cards remain easy to scan.
- As a user, I want to click from a preview card to a full idea page so that I can read the complete submission.
- As a user, I want to register and receive a confirmation outcome so that I know my account is ready.
- As a user, I want to log in using my validated identity details so that access is secure.
- As a user, I want idea form fields to prefill from my account when possible so that submission is faster.
- As a user, I want my own ideas listed in My Ideas so that I can manage my submissions in one place.
- As a user, I want date-range and preset filters in My Ideas so that I can find specific submissions.
- As a user, I want to edit or delete only my own ideas so that I stay in control of my content.
- As a user, I want matching previously anonymous ideas to be linked to my account so that my submission history stays complete.
- As a user, I want passwords to enforce strong policy (minimum length 12) so that accounts are harder to compromise.
- As a user, I want secure password-reset flows so that account recovery remains safe.

### Admin Stories

- As an admin, I want to review unallocated ideas so that no valuable community input is lost.
- As an admin, I want idea records preserved after account deletion so that historical submissions remain available.

## Key Routes

- `/` Home page
- `/about/` Redirect to home About section
- `/post/<slug>/` Full article detail
- `/how-to-2fa/` 2FA guide
- `/ideas/` Share Ideas form
- `/ideas/<id>/` Full idea detail
- `/ideas/my/` My Ideas (auth required)
- `/ideas/unallocated/` Unallocated ideas (admin only)
- `/login/`, `/register/`, `/settings/`
- `/forgot-password/`, `/reset-password/<uidb64>/<token>/`
- API endpoints under `/API/*` for login, registration, password reset, token refresh, logout, and account deletion

## Tech Stack

- Python 3.12
- Django 4.2
- SQLite (local default) / PostgreSQL via `DATABASE_URL` (deployment)
- WhiteNoise for static assets
- Argon2 primary password hasher
- Django REST Framework + SimpleJWT for API auth flows

## Local Development Setup

### Prerequisites

- Python 3.12+
- pip
- Git

### Install and Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Optional: Create an Admin User

```powershell
python manage.py createsuperuser
```

### Optional: Load Fixtures

```powershell
python manage.py loaddata fixtures/password_posts.json
python manage.py loaddata fixtures/posts.json
```

## Testing and Validation

```powershell
python manage.py test blog
python manage.py check
```

`pytest` is configured via [pytest.ini](pytest.ini) if you prefer a pytest workflow.

## Environment Variables

### Required for Production

- `SECRET_KEY`
- `DATABASE_URL`

### Common Optional Settings

- `DEBUG`
- `ALLOWED_HOSTS`
- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`
- `ADMIN_EMAIL`
- `IDEA_NOTIFICATION_RECIPIENTS`
- `IDEA_SUBMISSION_LIMIT`
- `IDEA_SUBMISSION_WINDOW_SECONDS`

### Security Notes

- Password minimum length is set to 12.
- Argon2 is the primary password hash algorithm.
- Local development can use console email backend by default.

## Deployment Notes

The project is set up for Heroku-style process execution:

- Release: `python manage.py migrate && python manage.py collectstatic --noinput`
- Web: `gunicorn password_app.wsgi --log-file -`

Defined in [Procfile](Procfile).

## Diagrams

- Mermaid ER source: [ERDiagram.md](ERDiagram.md)
- Graphviz ER source: [ERDiagram.dot](ERDiagram.dot)
