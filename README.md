# password_space_blog

Password Safe Blog is a Django web application focused on practical password security, account protection, and community-led cybersecurity education. The site combines security articles, a merged home/about landing page, a 2FA guide, secure account flows, and an ideas area where readers can suggest future topics.

## Core Features

- Merged Home and About landing page with blog mission, security guidance, and latest articles.
- Article detail pages for reading full cybersecurity posts.
- Community ideas area for submitting, viewing, editing, and deleting ideas.
- Account registration, login, logout, settings, and password reset flows.
- Dedicated 2FA how-to guide for practical account protection.
- Admin access to unallocated ideas.
- Security controls including strong password validation, rate limiting, and bot protection on idea submissions.

## Local Setup

### Prerequisites

- Python 3.12 
- pip
- Git

### Installation

1. Clone the repository.
2. Create a virtual environment.
3. Install the dependencies.
4. Run migrations.
5. Start the development server.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Optional Admin Setup

Create an admin account if you need access to Django admin or admin-only features.

```powershell
python manage.py createsuperuser
```

### Local Database Behavior

- Local development uses SQLite automatically when `DATABASE_URL` is not set.
- Production uses PostgreSQL through `DATABASE_URL`.

## Environment Variables

### Required in Production

- `SECRET_KEY`: Django secret key.
- `DATABASE_URL`: Database connection string.

### Common Optional Settings

- `DEBUG`
- `ALLOWED_HOSTS`
- `DEFAULT_FROM_EMAIL`
- `ADMIN_EMAIL`
- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `IDEA_NOTIFICATION_RECIPIENTS`
- `IDEA_SUBMISSION_LIMIT`
- `IDEA_SUBMISSION_WINDOW_SECONDS`

### Notes

- When `DEBUG=True` locally, the project falls back to a local development secret key if `SECRET_KEY` is not provided.
- Password reset emails use the console backend locally unless email settings are supplied.
- The password policy enforces a minimum length of 12 characters.

## Deployment

This project is configured for Heroku-style deployment.

### Procfile Behavior

- Release phase: `python manage.py migrate && python manage.py collectstatic --noinput`
- Web process: `gunicorn password_app.wsgi --log-file -`

### Deployment Checklist

1. Set production environment variables, especially `SECRET_KEY`, `DATABASE_URL`, and any email settings.
2. Push the latest code to the deployment remote.
3. Confirm migrations and static collection complete successfully.
4. Smoke-test the main routes after deployment.

### Suggested Smoke Tests

- `/`
- `/about/`
- `/how-to-2fa/`
- `/ideas/`
- one `/post/<slug>/` page

## User Stories

### User Stories

- As a user, I want to browse the latest security articles on the home page so that I can quickly find practical password guidance.
- As a user, I want to open a full article page so that I can read detailed cybersecurity advice and examples.
- As a user, I want to understand what the blog is about from the home page so that I can decide whether the content is relevant to me.
- As a user, I want to access a step-by-step 2FA guide so that I can improve the security of my important accounts.
- As a user, I want to submit an idea for a future article so that I can influence the topics covered by the blog.
- As a user, I want to register for an account so that I can manage my submissions and participate more fully in the site.
- As a user, I want to reset my password if I forget it so that I can regain access securely.

### Registered User Stories

- As a registered user, I want to log in securely so that I can access my account features.
- As a registered user, I want my name and email to prefill on the ideas form when appropriate so that submitting ideas is faster.
- As a registered user, I want to view my submitted ideas in one place so that I can keep track of what I have shared.
- As a registered user, I want to filter my ideas by time period or date range so that I can find older submissions more easily.
- As a registered user, I want to edit my own ideas so that I can improve or correct them after submission.
- As a registered user, I want to delete my own ideas so that I stay in control of my content.
- As a registered user, I want to manage my account settings so that I can keep my account details up to date.

### Admin Stories

- As an admin, I want to access unallocated ideas so that I can review submissions that are no longer attached to an account owner.
- As an admin, I want community ideas to remain available after account changes so that valuable content suggestions are not lost.

### Security Stories

- As a user, I want password validation to require strong credentials, including a minimum length of 12 characters, so that my account is better protected.
- As a user, I want secure password reset flows so that account recovery does not weaken site security.
- As a site owner, I want idea submissions to be rate-limited and protected against simple bots so that the ideas area remains useful and manageable.

## Project Epics

### Epic 1: Content Discovery

Focus: Help visitors find, understand, and read cybersecurity content quickly.

- Includes browsing the home page, viewing article excerpts, opening full post pages, and understanding the purpose of the blog.

### Epic 2: Community Contribution

Focus: Allow visitors and registered users to contribute content ideas and engage with the blog direction.

- Includes idea submission, viewing community ideas, and encouraging story sharing.

### Epic 3: Account Management

Focus: Give users secure access to registration, login, password recovery, and account settings.

- Includes account creation, secure authentication, password reset, and profile-linked submissions.

### Epic 4: User-Owned Content Management

Focus: Allow authenticated users to manage ideas they have submitted.

- Includes viewing, filtering, editing, and deleting personal ideas.

### Epic 5: Admin Oversight and Security Controls

Focus: Protect the platform and preserve community content over time.

- Includes unallocated idea review, submission protection, and strong password policy enforcement.

## Acceptance Criteria

### Home and Content Browsing

- Given a user lands on the home page, when the page loads, then they can see the blog introduction, About section, latest articles, and latest community ideas.
- Given a user clicks a latest article, when the destination opens, then the full article page is displayed.
- Given a user opens `/about/`, when the request is processed, then they are redirected to the Home page About section.

### Ideas Submission and Participation

- Given a user completes the ideas form with valid details, when they submit it, then the idea is saved and a success message is shown.
- Given an authenticated user opens the ideas page, when the form renders, then their account details can be prefilled where available.
- Given a user views the ideas page, when community ideas exist, then the submitted ideas are listed.

### User Account Flows

- Given a new user provides valid registration details, when they submit the form, then an account is created successfully.
- Given a user enters a password that does not meet policy requirements, when they try to register or reset it, then the request is rejected with a validation message.
- Given a user forgets their password, when they request a reset and provide valid information, then they can complete the reset flow securely.

### My Ideas Management

- Given an authenticated user opens My Ideas, when the page loads, then they can see their submitted ideas.
- Given an authenticated user applies a date filter, when the filter is submitted, then only matching ideas are shown.
- Given an authenticated user edits or deletes one of their own ideas, when the action is confirmed, then the change is saved.

### Admin and Security Controls

- Given an admin opens the unallocated ideas area, when unowned ideas exist, then they are visible for review.
- Given repeated idea submissions exceed the configured rate limit, when another submission is attempted, then the request is blocked with an appropriate message.
- Given a bot fills the honeypot field, when the form is submitted, then the submission is not processed as a real user submission.






















