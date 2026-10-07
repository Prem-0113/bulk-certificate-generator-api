from django.urls import path

from certificates_api.views import (
    CertificateDownloadView,
    CertificateJobDetailView,
    DownloadAllCertificatesView,
    GenerateCertificateJobView,
)

urlpatterns = [
    path("api/certificates/generate/", GenerateCertificateJobView.as_view(), name="generate-certificate-job"),
    path("api/certificates/jobs/<uuid:job_id>/", CertificateJobDetailView.as_view(), name="certificate-job-detail"),
    path("api/certificates/<uuid:certificate_id>/download/", CertificateDownloadView.as_view(), name="certificate-download"),
    path("api/certificates/jobs/<uuid:job_id>/download-all/", DownloadAllCertificatesView.as_view(), name="download-all-certificates"),
]
