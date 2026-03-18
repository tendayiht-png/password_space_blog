"""Local environment configuration.

Edit values in ENV_OVERRIDES and keep secrets out of version control.
Only non-empty, non-placeholder values are applied.
"""

import os


ENV_OVERRIDES = {
	# SMTP setup:
	# 1) Fill EMAIL_HOST_USER and EMAIL_HOST_PASSWORD with real credentials.
	# 2) Set DEFAULT_FROM_EMAIL to a verified sender mailbox.
	# 3) Keep EMAIL_BACKEND empty to let settings auto-detect SMTP, or set
	#    it explicitly to django.core.mail.backends.smtp.EmailBackend.
	'EMAIL_BACKEND': '',
	'EMAIL_HOST': 'smtp.gmail.com',
	'EMAIL_PORT': '587',
	'EMAIL_USE_TLS': 'True',
	'EMAIL_HOST_USER': 'admin',
	'EMAIL_HOST_PASSWORD': 'TempPassword123!',
	'DEFAULT_FROM_EMAIL': 'tendayiht@gmail.com',
}


def _is_placeholder(value):
	"""Return True when a value still uses placeholder markers."""
	text = str(value).strip()
	return text.startswith('<') and text.endswith('>')


def load_env():
	"""Apply local overrides without replacing existing process env vars."""
	for key, value in ENV_OVERRIDES.items():
		if value == '' or _is_placeholder(value):
			continue
		os.environ.setdefault(key, str(value))


load_env()
