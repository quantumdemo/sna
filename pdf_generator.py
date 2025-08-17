from flask import render_template
from weasyprint import HTML
import os

def generate_certificate_pdf(certificate, user, course, app):
    with app.app_context():
        rendered_html = render_template(
            'certificate/template.html',
            student_name=user.name,
            course_name=course.title,
            completion_date=certificate.issued_at.strftime('%Y-%m-%d'),
            certificate_id=certificate.certificate_uid
        )

    pdf_folder = os.path.join(app.static_folder, 'certificates')
    os.makedirs(pdf_folder, exist_ok=True)

    file_path = os.path.join(pdf_folder, f'{certificate.certificate_uid}.pdf')

    HTML(string=rendered_html).write_pdf(file_path)

    # The path should be relative to the static folder for url_for to work
    # and must use forward slashes for URL compatibility.
    certificate.file_path = f"certificates/{certificate.certificate_uid}.pdf"
    return certificate
