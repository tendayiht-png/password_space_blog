"""Local environment configuration.

Edit values in ENV_OVERRIDES and keep secrets out of version control.
Only non-empty values are applied.
"""

import os


ENV_OVERRIDES = {
	# Leave EMAIL_BACKEND empty to let settings auto-detect SMTP when
	# credentials are provided, otherwise it will use the console backend.
	'EMAIL_BACKEND': '',
	'EMAIL_HOST': 'smtp.gmail.com',
	'EMAIL_PORT': '587',
	'EMAIL_USE_TLS': 'True',
	'EMAIL_HOST_USER': '',
	'EMAIL_HOST_PASSWORD': '',
	'DEFAULT_FROM_EMAIL': '',
}


def load_env():
	"""Apply local overrides without replacing existing process env vars."""
	for key, value in ENV_OVERRIDES.items():
		if value == '':
			continue
		os.environ.setdefault(key, str(value))


load_env()
