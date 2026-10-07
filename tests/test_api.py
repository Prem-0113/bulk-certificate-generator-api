from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from certificates_api.models import Certificate, CertificateJob
from certificates_api.tasks import generate_certificates_for_job


class CertificateJobTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_valid_job_creation_and_202_response(self):
        payload = {
            "title": "Python Foundations",
            "recipients": [
                {"name": "Alice Johnson", "email": "alice@example.com", "course": "Python Foundations"},
                {"name": "Bob Smith", "email": "bob@example.com", "course": "Python Foundations"},
            ],
        }

        response = self.client.post("/api/certificates/generate/", payload, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertIn("job_id", response.data)
        self.assertEqual(response.data["status"], "PENDING")

        job = CertificateJob.objects.get(id=response.data["job_id"])
        self.assertEqual(job.total_records, 2)
        self.assertEqual(job.success_count, 2)
        self.assertEqual(job.failed_count, 0)
        self.assertEqual(job.status, "COMPLETED")

    def test_payload_validation_rejects_malformed_data(self):
        payload = {
            "title": "Broken Job",
            "recipients": [{"name": "", "email": "bad-email", "course": "Python"}],
        }

        response = self.client.post("/api/certificates/generate/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_background_task_handles_partial_failures(self):
        payload = {
            "title": "Advanced UX",
            "recipients": [
                {"name": "Dora Miller", "email": "dora@example.com", "course": "Advanced UX", "trigger_failure": True},
                {"name": "Evan Lee", "email": "evan@example.com", "course": "Advanced UX"},
            ],
        }

        response = self.client.post("/api/certificates/generate/", payload, format="json")
        job = CertificateJob.objects.get(id=response.data["job_id"])

        self.assertEqual(job.status, "COMPLETED")
        self.assertEqual(job.success_count, 1)
        self.assertEqual(job.failed_count, 1)
        self.assertEqual(job.certificates.filter(status="SUCCESS").count(), 1)
        self.assertEqual(job.certificates.filter(status="FAILED").count(), 1)

    def test_job_detail_endpoint_reports_progress(self):
        job = CertificateJob.objects.create(
            title="Course Completion",
            status="COMPLETED",
            total_records=1,
            success_count=1,
            failed_count=0,
            recipients=[{"name": "Frank Hill", "email": "frank@example.com", "course": "Security Basics"}],
        )
        cert = Certificate.objects.create(
            job=job,
            recipient_name="Frank Hill",
            recipient_email="frank@example.com",
            status="SUCCESS",
            certificate_file="certificates/frank.png",
        )

        media_dir = Path(settings.MEDIA_ROOT) / "certificates"
        media_dir.mkdir(parents=True, exist_ok=True)
        file_path = media_dir / "frank.png"
        Image.new("RGB", (800, 600), "white").save(file_path)

        response = self.client.get(f"/api/certificates/jobs/{job.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["successful_count"], 1)
        self.assertEqual(response.data["certificates"][0]["recipient_name"], "Frank Hill")

        download_response = self.client.get(f"/api/certificates/{cert.id}/download/")
        self.assertEqual(download_response.status_code, 200)
        self.assertTrue(download_response.get("Content-Type").startswith("application/octet-stream"))

    def test_download_all_returns_zip_archive(self):
        job = CertificateJob.objects.create(
            title="Certificate Batch",
            status="COMPLETED",
            total_records=2,
            success_count=2,
            failed_count=0,
            recipients=[
                {"name": "Alice", "email": "alice@example.com", "course": "Python"},
                {"name": "Bob", "email": "bob@example.com", "course": "Python"},
            ],
        )

        media_dir = Path(settings.MEDIA_ROOT) / "certificates"
        media_dir.mkdir(parents=True, exist_ok=True)

        for index, name in enumerate(["alice", "bob"], start=1):
            file_path = media_dir / f"{name}.png"
            Image.new("RGB", (800, 600), "white").save(file_path)
            Certificate.objects.create(
                job=job,
                recipient_name=name.title(),
                recipient_email=f"{name}@example.com",
                status="SUCCESS",
                certificate_file=f"certificates/{name}.png",
            )

        response = self.client.get(f"/api/certificates/jobs/{job.id}/download-all/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("certificates_", response["Content-Disposition"])

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_task_executes_and_creates_certificate_files(self):
        job = CertificateJob.objects.create(
            title="Automation Test",
            status="PENDING",
            total_records=1,
            recipients=[{"name": "Carla Jones", "email": "carla@example.com", "course": "Data Science Basics"}],
        )

        result = generate_certificates_for_job(str(job.id))
        self.assertEqual(result["status"], "COMPLETED")
        job.refresh_from_db()
        self.assertEqual(job.success_count, 1)
        self.assertEqual(job.certificates.count(), 1)
        self.assertEqual(job.certificates.first().status, "SUCCESS")
