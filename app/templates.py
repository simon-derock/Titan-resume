"""Reviewed resume-template catalog and immutable selection metadata."""

from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import ResumeTemplateId


class TemplateProfile(BaseModel):
    """Versioned document characteristics for one supported template."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    template_id: ResumeTemplateId
    display_name: str = Field(min_length=1)
    template_file: str = Field(pattern=r"^[a-z0-9_]+\.tex\.j2$")
    layout: Literal["single_column", "two_column"]
    page_size: Literal["A4"] = "A4"
    source_url: str | None = None
    license_id: str = Field(min_length=1)


SUPPORTED_TEMPLATE_IDS: tuple[ResumeTemplateId, ...] = (
    "resume_v1",
    "moderncv_two_column_v1",
    "deedy_cv_v1",
)

_TEMPLATE_PROFILES = MappingProxyType(
    {
        "resume_v1": TemplateProfile(
            template_id="resume_v1",
            display_name="TITAN ATS",
            template_file="resume_v1.tex.j2",
            layout="single_column",
            license_id="TITAN",
        ),
        "moderncv_two_column_v1": TemplateProfile(
            template_id="moderncv_two_column_v1",
            display_name="ModernCV Two Column",
            template_file="moderncv_two_column_v1.tex.j2",
            layout="two_column",
            source_url=(
                "https://www.overleaf.com/latex/templates/"
                "two-column-cv-template-with-moderncv/mqycjnmnswzz"
            ),
            license_id="LPPL-1.3c",
        ),
        "deedy_cv_v1": TemplateProfile(
            template_id="deedy_cv_v1",
            display_name="Deedy CV",
            template_file="deedy_cv_v1.tex.j2",
            layout="two_column",
            source_url=(
                "https://www.overleaf.com/latex/templates/deedy-cv/bjryvfsjdyxz"
            ),
            license_id="Apache-2.0",
        ),
    }
)


def get_template_profile(template_id: ResumeTemplateId) -> TemplateProfile:
    """Return the reviewed profile for a schema-validated template ID."""

    return _TEMPLATE_PROFILES[template_id]
