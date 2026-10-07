import os
import uuid
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def generate_certificate_png(recipient_name: str, course_name: str, issuer_name: str, issue_date: str) -> tuple[str, str]:
    base_template = Path(settings.BASE_DIR) / "assets" / "template.png"
    if not base_template.exists():
        raise FileNotFoundError(f"Certificate template not found at {base_template}")

    with Image.open(base_template) as template:
        image = template.copy()

    draw = ImageDraw.Draw(image)
    width, height = image.size

    # Title
    title_font = _get_font(52, bold=True)
    title_text = "Certificate of Completion"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_width) / 2, 80), title_text, fill="#1b2a3a", font=title_font)

    # Recipient name
    name_font = _get_font(56, bold=True)
    recipient_text = recipient_name.upper()
    name_bbox = draw.textbbox((0, 0), recipient_text, font=name_font)
    name_width = name_bbox[2] - name_bbox[0]
    draw.text(((width - name_width) / 2, 260), recipient_text, fill="#0b2545", font=name_font)

    # Divider line
    draw.line((260, 360, width - 260, 360), fill="#d9b72b", width=4)

    # Course text
    body_font = _get_font(30)
    course_text = f"has successfully completed the course: {course_name}"
    body_bbox = draw.textbbox((0, 0), course_text, font=body_font)
    body_width = body_bbox[2] - body_bbox[0]
    draw.text(((width - body_width) / 2, 420), course_text, fill="#243b53", font=body_font)

    # Issuer and date
    meta_font = _get_font(26)
    issuer_text = f"Issued by: {issuer_name}"
    date_text = f"Date: {issue_date}"
    draw.text((140, 560), issuer_text, fill="#243b53", font=meta_font)
    draw.text((width - 340, 560), date_text, fill="#243b53", font=meta_font)

    output_dir = Path(settings.MEDIA_ROOT) / "certificates"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(ch if ch.isalnum() else "-" for ch in recipient_name.lower()).strip("-")
    file_name = f"{safe_name or 'certificate'}-{uuid.uuid4().hex}.png"
    output_path = output_dir / file_name
    image.save(output_path)
    return str(output_path), file_name
