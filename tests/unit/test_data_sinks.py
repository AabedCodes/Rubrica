import csv
from io import StringIO
from uuid import UUID

import pytest

from backend.sinks.csv_export import render_csv
from backend.sinks.grade_email import build_grade_email, send_grade_email
from backend.sinks.text_policy import clean_model_text


def test_csv_formula_cells_are_prefixed_and_quoted():
    values = ("=CANARY-T34-3e40", "+1", "-1", "@test", "\tvalue", "\rvalue", 'plain,"text"')
    exported = render_csv(("value",), [(value,) for value in values])
    parsed = list(csv.reader(StringIO(exported, newline="")))
    assert parsed == [["value"], *[["'" + value] for value in values[:6]], [values[-1]]]
    assert exported.startswith('"value"\r\n')


def test_release_notification_uses_roster_and_one_app_link():
    course = UUID(int=1)
    mail = build_grade_email(
        roster_email="student-1-01@example.edu",
        assignment_title="Project\r\nPart 1",
        course_code="DEMO01",
        base_url="http://127.0.0.1:8080",
        course_id=course,
    )
    assert str(mail["To"]) == "student-1-01@example.edu"
    assert str(mail["From"]) == "Rubrica <no-reply@rubrica.example.edu>"
    assert mail["Subject"] == "Your grade for Project Part 1 is available"
    assert f"http://127.0.0.1:8080/courses/{course}/grades" in mail.get_content()
    assert mail.get_content_type() == "text/plain"
    with pytest.raises(ValueError, match="require Mailpit"):
        send_grade_email(mail, smtp_host="example.edu")


def test_model_text_drops_images_and_html_but_preserves_links_and_text():
    source = (
        "Before ![inline](https://example.edu/image) ![reference][picture] "
        "[course][link] <em>after</em>\n\n"
        "[picture]: https://example.edu/ref\n"
        "[link]: https://example.edu/course\n\n"
        "<div>Block text</div>"
    )
    result = clean_model_text(source)
    assert result.count("[image removed]") == 2
    assert "[course](https://example.edu/course)" in result
    assert "after" in result and "Block text" in result
    assert "https://example.edu/image" not in result
    assert "https://example.edu/ref" not in result
    assert "<em>" not in result and "<div>" not in result


def test_escaped_image_syntax_stays_literal_after_normalizing():
    source = r"\![literal](https://example.edu/marker)"
    assert clean_model_text(clean_model_text(source)) == clean_model_text(source)
    assert "[image removed]" not in clean_model_text(source)
