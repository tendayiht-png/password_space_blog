release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn password_app.wsgi --log-file -
