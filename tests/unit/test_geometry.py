import pytest

from app.models import GeometryPolicy, PageGeometry, TextBox
from app.services.validation import GeometryValidator


@pytest.mark.unit
def test_geometry_validator_accepts_text_inside_safe_margins() -> None:
    geometry = PageGeometry(
        width_pt=595.0,
        height_pt=842.0,
        text_boxes=(
            TextBox(
                element_id="header",
                text="Alex Morgan",
                x0=24.0,
                y0=20.0,
                x1=570.0,
                y1=820.0,
            ),
        ),
    )

    report = GeometryValidator(policy=GeometryPolicy()).validate(geometry)

    assert report.passed is True
    assert report.issues == ()
    assert report.minimum_left_margin_pt == 24.0
    assert report.minimum_bottom_margin_pt == 22.0


@pytest.mark.unit
def test_geometry_validator_reports_text_crossing_safe_left_margin() -> None:
    geometry = PageGeometry(
        width_pt=595.0,
        height_pt=842.0,
        text_boxes=(
            TextBox(
                element_id="experience.titan.bullet_1",
                text="Built a compiler.",
                x0=18.0,
                y0=24.0,
                x1=560.0,
                y1=40.0,
            ),
        ),
    )

    report = GeometryValidator(policy=GeometryPolicy()).validate(geometry)

    assert report.passed is False
    assert len(report.issues) == 1
    issue = report.issues[0]
    assert issue.source == "geometry"
    assert issue.element_id == "experience.titan.bullet_1"
    assert issue.issue_type == "unsafe_margin"
    assert issue.severity == "fatal"
    assert issue.measured_value == 18.0
    assert issue.expected_value == 22.0


@pytest.mark.unit
def test_geometry_validator_reports_text_crossing_safe_bottom_margin() -> None:
    geometry = PageGeometry(
        width_pt=595.0,
        height_pt=842.0,
        text_boxes=(
            TextBox(
                element_id="skills.languages",
                text="Languages: Python",
                x0=24.0,
                y0=810.0,
                x1=560.0,
                y1=826.0,
            ),
        ),
    )

    report = GeometryValidator(policy=GeometryPolicy()).validate(geometry)

    assert report.passed is False
    assert report.issues[0].issue_type == "unsafe_margin"
    assert report.issues[0].measured_value == 16.0
    assert report.issues[0].expected_value == 20.0


@pytest.mark.unit
def test_geometry_validator_rejects_excessive_bottom_whitespace() -> None:
    geometry = PageGeometry(
        width_pt=595.0,
        height_pt=842.0,
        text_boxes=(
            TextBox(
                element_id="education.degree",
                text="B.Tech in Artificial Intelligence and Data Science",
                x0=24.0,
                y0=510.0,
                x1=570.0,
                y1=530.0,
            ),
        ),
    )

    report = GeometryValidator(policy=GeometryPolicy()).validate(geometry)

    assert report.passed is False
    assert len(report.issues) == 1
    issue = report.issues[0]
    assert issue.source == "geometry"
    assert issue.element_id == "education.degree"
    assert issue.issue_type == "excessive_bottom_whitespace"
    assert issue.severity == "high"
    assert issue.measured_value == 312.0
    assert issue.expected_value == 60.0


@pytest.mark.unit
def test_geometry_validator_accepts_page_at_maximum_bottom_whitespace() -> None:
    geometry = PageGeometry(
        width_pt=595.0,
        height_pt=842.0,
        text_boxes=(
            TextBox(
                element_id="education.degree",
                text="B.Tech in Artificial Intelligence and Data Science",
                x0=24.0,
                y0=762.0,
                x1=570.0,
                y1=782.0,
            ),
        ),
    )

    report = GeometryValidator(policy=GeometryPolicy()).validate(geometry)

    assert report.passed is True
    assert report.issues == ()
