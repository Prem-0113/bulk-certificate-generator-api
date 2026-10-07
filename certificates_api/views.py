import io
import zipfile
from pathlib import Path

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from certificates_api.models import Certificate, CertificateJob
from certificates_api.serializers import GenerateCertificateJobSerializer
from certificates_api.tasks import generate_certificates_for_job


class GenerateCertificateJobView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = GenerateCertificateJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        recipients = validated["recipients"]

        job = CertificateJob.objects.create(
            title=validated.get("title", "Certificate Generation Job"),
            total_records=len(recipients),
            recipients=recipients,
            status=CertificateJob.STATUS_PENDING,
        )

        try:
            generate_certificates_for_job.delay(str(job.id))
        except Exception:
            generate_certificates_for_job.apply(args=[str(job.id)])

        return Response(
            {"job_id": str(job.id), "status": job.status},
            status=status.HTTP_202_ACCEPTED,
        )


class CertificateJobDetailView(APIView):
    def get(self, request, job_id, *args, **kwargs):
        job = get_object_or_404(CertificateJob, id=job_id)
        certificates = job.certificates.all().order_by("created_at")

        payload = {
            "job_id": str(job.id),
            "title": job.title,
            "status": job.status,
            "total_records": job.total_records,
            "successful_count": job.success_count,
            "failed_count": job.failed_count,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "certificates": [
                {
                    "certificate_id": str(certificate.id),
                    "recipient_name": certificate.recipient_name,
                    "recipient_email": certificate.recipient_email,
                    "status": certificate.status,
                    "error_message": certificate.error_message,
                    "download_url": request.build_absolute_uri(
                        reverse("certificate-download", kwargs={"certificate_id": certificate.id})
                    ) if certificate.certificate_file else None,
                }
                for certificate in certificates
            ],
        }
        return Response(payload)


class CertificateDownloadView(APIView):
    def get(self, request, certificate_id, *args, **kwargs):
        certificate = get_object_or_404(Certificate, id=certificate_id)
        if not certificate.certificate_file or not certificate.certificate_file.name:
            raise Http404("Certificate file is not available.")

        file_path = Path(certificate.certificate_file.path)
        if not file_path.exists():
            raise Http404("Certificate file missing from storage.")

        return FileResponse(
            file_path.open("rb"),
            as_attachment=True,
            filename=file_path.name,
            content_type="application/octet-stream",
        )


class DownloadAllCertificatesView(APIView):
    def get(self, request, job_id, *args, **kwargs):
        job = get_object_or_404(CertificateJob, id=job_id)
        certificates = job.certificates.filter(status=Certificate.STATUS_SUCCESS).order_by("created_at")

        if not certificates.exists():
            return Response({"detail": "No successful certificates found for this job."}, status=status.HTTP_404_NOT_FOUND)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for certificate in certificates:
                if not certificate.certificate_file or not certificate.certificate_file.name:
                    continue
                file_path = Path(certificate.certificate_file.path)
                if file_path.exists():
                    archive.write(file_path, arcname=file_path.name)

        zip_buffer.seek(0)
        return FileResponse(
            zip_buffer,
            as_attachment=True,
            filename=f"certificates_{job.id}.zip",
            content_type="application/zip",
        )
