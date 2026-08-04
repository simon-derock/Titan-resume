import pytest
from pydantic import ValidationError

from app.models import ResumeContent
from app.templates import SUPPORTED_TEMPLATE_IDS, get_template_profile


EXPECTED_TEMPLATE_IDS = (
    "resume_v1",
    "moderncv_two_column_v1",
    "deedy_cv_v1",
)


@pytest.mark.contract
def test_supported_template_catalog_is_explicit_and_versioned() -> None:
    assert SUPPORTED_TEMPLATE_IDS == EXPECTED_TEMPLATE_IDS

    profiles = tuple(
        get_template_profile(template_id) for template_id in SUPPORTED_TEMPLATE_IDS
    )
    assert tuple(profile.template_id for profile in profiles) == EXPECTED_TEMPLATE_IDS
    assert tuple(profile.layout for profile in profiles) == (
        "single_column",
        "two_column",
        "two_column",
    )
    assert all(profile.page_size == "A4" for profile in profiles)
    assert all(profile.template_file.endswith(".tex.j2") for profile in profiles)


@pytest.mark.contract
@pytest.mark.parametrize("template_id", EXPECTED_TEMPLATE_IDS)
def test_resume_content_accepts_every_supported_template(template_id: str) -> None:
    content = ResumeContent(
        resume_id="resume.template_contract.001",
        target_role="AI Engineer",
        template_id=template_id,
    )

    assert content.template_id == template_id


@pytest.mark.contract
def test_resume_content_rejects_an_unregistered_template() -> None:
    with pytest.raises(ValidationError):
        ResumeContent(
            resume_id="resume.template_contract.001",
            target_role="AI Engineer",
            template_id="unreviewed_template",
        )


@pytest.mark.contract
def test_third_party_template_profiles_retain_source_and_license_metadata() -> None:
    moderncv = get_template_profile("moderncv_two_column_v1")
    deedy = get_template_profile("deedy_cv_v1")

    assert moderncv.source_url == (
        "https://www.overleaf.com/latex/templates/"
        "two-column-cv-template-with-moderncv/mqycjnmnswzz"
    )
    assert moderncv.license_id == "LPPL-1.3c"
    assert deedy.source_url == (
        "https://www.overleaf.com/latex/templates/deedy-cv/bjryvfsjdyxz"
    )
    assert deedy.license_id == "Apache-2.0"
