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
                y1=820.0,
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


@pytest.mark.unit
def test_geometry_validator_rejects_deedy_column_depth_beyond_reference() -> None:
    """The 16% tolerance admits the 116.4pt handmade baseline, not 550pt gaps."""
    geometry = PageGeometry(
        width_pt=595.0,
        height_pt=842.0,
        text_boxes=(
            TextBox(
                element_id="header",
                text="Alex Morgan",
                x0=180.0,
                y0=20.0,
                x1=410.0,
                y1=40.0,
            ),
            TextBox(
                element_id="skills.heading",
                text="SKILLS",
                x0=35.0,
                y0=120.0,
                x1=90.0,
                y1=132.0,
            ),
            TextBox(
                element_id="experience.heading",
                text="EXPERIENCE",
                x0=224.0,
                y0=120.0,
                x1=310.0,
                y1=132.0,
            ),
            TextBox(
                element_id="skills.last",
                text="Python",
                x0=35.0,
                y0=240.0,
                x1=80.0,
                y1=250.0,
            ),
            TextBox(
                element_id="projects.last",
                text="FastAPI",
                x0=224.0,
                y0=790.0,
                x1=280.0,
                y1=800.0,
            ),
        ),
    )

    report = GeometryValidator(policy=GeometryPolicy()).validate(
        geometry,
        template_id="deedy_cv_v1",
    )

    assert report.passed is False
    assert report.column_bottom_delta_pt == 550.0
    issue = report.issues[0]
    assert issue.issue_type == "column_imbalance"
    assert issue.severity == "high"
    assert issue.measured_value == 550.0
    assert issue.expected_value == pytest.approx(134.72)


@pytest.mark.unit
def test_geometry_validator_accepts_handmade_column_depth_baseline() -> None:
    geometry = PageGeometry(
        width_pt=612.0,
        height_pt=792.0,
        text_boxes=(
            TextBox(
                element_id="education.heading",
                text="EDUCATION",
                x0=26.0,
                y0=100.0,
                x1=150.0,
                y1=118.0,
            ),
            TextBox(
                element_id="experience.heading",
                text="EXPERIENCE",
                x0=309.0,
                y0=100.0,
                x1=449.0,
                y1=118.0,
            ),
            TextBox(
                element_id="research.last",
                text="Research",
                x0=26.0,
                y0=643.6,
                x1=90.0,
                y1=653.6,
            ),
            TextBox(
                element_id="projects.last",
                text="re-identification",
                x0=360.0,
                y0=760.0,
                x1=450.0,
                y1=770.0,
            ),
        ),
    )

    report = GeometryValidator(policy=GeometryPolicy()).validate(
        geometry,
        template_id="deedy_cv_v1",
    )

    assert report.column_bottom_delta_pt == pytest.approx(116.4)
    assert report.passed is True
