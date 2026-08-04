"""Deterministic physical space planning for the locked resume template."""

from app.models import (
    ResumeSpaceBudget,
    SectionSpaceBudget,
    SpacePlanningPolicy,
)


class SpacePlanner:
    """Translate available content into fixed one-page section ceilings."""

    def __init__(self, *, policy: SpacePlanningPolicy | None = None) -> None:
        self._policy = policy or SpacePlanningPolicy()

    def plan(
        self,
        *,
        available_experience_entries: int,
        available_project_entries: int,
        available_education_entries: int,
    ) -> ResumeSpaceBudget:
        """Cap available entries while preserving reviewed physical limits."""

        available_counts = (
            available_experience_entries,
            available_project_entries,
            available_education_entries,
        )
        if any(count < 0 for count in available_counts):
            raise ValueError("available entry counts must be non-negative")

        policy = self._policy
        return ResumeSpaceBudget(
            total_line_limit=policy.total_line_limit,
            header_line_limit=policy.header_line_limit,
            summary_line_limit=policy.summary_line_limit,
            experience=SectionSpaceBudget(
                section="experience",
                line_limit=policy.experience_line_limit,
                entry_limit=min(
                    available_experience_entries,
                    policy.experience_entry_limit,
                ),
                bullets_per_entry_limit=(policy.experience_bullets_per_entry_limit),
            ),
            projects=SectionSpaceBudget(
                section="projects",
                line_limit=policy.project_line_limit,
                entry_limit=min(
                    available_project_entries,
                    policy.project_entry_limit,
                ),
                bullets_per_entry_limit=policy.project_bullets_per_entry_limit,
            ),
            skills_line_limit=policy.skills_line_limit,
            education=SectionSpaceBudget(
                section="education",
                line_limit=policy.education_line_limit,
                entry_limit=min(
                    available_education_entries,
                    policy.education_entry_limit,
                ),
                bullets_per_entry_limit=0,
            ),
        )
