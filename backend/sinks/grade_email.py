"""Plain-text grade release notification (C08)."""

from email.headerregistry import Address
from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTP
from string import Template
from urllib.parse import urlsplit
from uuid import UUID

SENDER = Address("Rubrica", addr_spec="no-reply@rubrica.example.edu")
TEMPLATE = Path(__file__).with_name("templates") / "grade_released.txt"


def build_grade_email(
    *, roster_email: str, assignment_title: str, course_code: str, base_url: str, course_id: UUID
) -> EmailMessage:
    title = " ".join(assignment_title.splitlines())
    code = " ".join(course_code.splitlines())
    app = urlsplit(base_url)
    if (
        app.scheme not in {"https", "http"}
        or not app.hostname
        or app.username is not None
        or app.query
        or app.fragment
        or any(char.isspace() for char in base_url)
    ):
        raise ValueError("Invalid app base URL")

    body = Template(TEMPLATE.read_text(encoding="utf-8")).substitute(
        assignment_title=title,
        course_code=code,
        grade_url=f"{base_url.rstrip('/')}/courses/{course_id}/grades",
    )
    message = EmailMessage()
    message["Subject"] = f"Your grade for {title} is available"
    message["From"] = SENDER
    message["To"] = Address(addr_spec=roster_email)
    message.set_content(body)
    return message


def send_grade_email(message: EmailMessage, *, smtp_host: str, smtp_port: int = 1025) -> None:
    if smtp_host != "mailpit":
        raise ValueError("Grade notifications require Mailpit")
    with SMTP(smtp_host, smtp_port, timeout=10) as smtp:
        smtp.send_message(message)
