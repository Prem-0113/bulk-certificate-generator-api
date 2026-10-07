from pathlib import Path

from celery import shared_task
from django.core.files import File

from certificates_api.models import Certificate, CertificateJob
from certificates_api.services.certificate_service import generate_certificate_png


@shared_task(bind=True)
def generate_certificates_for_job(self, job_id):
    job = CertificateJob.objects.get(id=job_id)
    job.status = CertificateJob.STATUS_PROCESSING
    job.save(update_fields=["status", "updated_at"])

    for recipient in job.recipients:
        name = str(recipient.get("name", "")).strip()
        email = str(recipient.get("email", "")).strip()
        course = str(recipient.get("course", "Certificate of Completion")).strip() or "Certificate of Completion"
        trigger_failure = bool(recipient.get("trigger_failure", False))

        if not name or not email:
            Certificate.objects.create(
                job=job,
                recipient_name=name or "Unknown Recipient",
                recipient_email=email or "invalid@example.com",
                status=Certificate.STATUS_FAILED,
                error_message="Recipient is missing a valid name or email.",
            )
            job.failed_count += 1
            continue

        try:
            if trigger_failure:
                raise ValueError("Simulated rendering failure for this recipient.")

            absolute_path, file_name = generate_certificate_png(
                recipient_name=name,
                course_name=course,
                issuer_name="Acme Learning",
                issue_date=job.created_at.strftime("%Y-%m-%d"),
            )

            with open(absolute_path, "rb") as file_handle:
                certificate = Certificate(
                    job=job,
                    recipient_name=name,
                    recipient_email=email,
                    status=Certificate.STATUS_SUCCESS,
                )
                certificate.certificate_file.save(file_name, File(file_handle), save=False)
                certificate.save()

            job.success_count += 1
        except Exception as exc:
            Certificate.objects.create(
                job=job,
                recipient_name=name,
                recipient_email=email,
                status=Certificate.STATUS_FAILED,
                error_message=str(exc),
            )
            job.failed_count += 1

    job.total_records = len(job.recipients)
    job.status = CertificateJob.STATUS_COMPLETED
    job.save(update_fields=["status", "total_records", "success_count", "failed_count", "updated_at"])
    return {"job_id": str(job.id), "status": job.status, "success": job.success_count, "failed": job.failed_count}
