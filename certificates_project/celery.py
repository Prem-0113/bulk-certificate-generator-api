import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "certificates_project.settings")

app = Celery("certificates_project")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
