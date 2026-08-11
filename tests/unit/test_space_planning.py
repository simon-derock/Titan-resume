import pytest
from pydantic import ValidationError

from app.models import SpacePlanningPolicy
from app.services.planning import SpacePlanner


def test_default_space_plan_stays_within_the_locked_page_budget() -> None:
    plan = SpacePlanner().plan(
        available_experience_entries=5,
        available_project_entries=6,
        available_education_entries=1,
    )

    assert plan.total_line_limit == 47
    assert plan.reserved_line_count == 47
    assert plan.header_line_limit == 3
    assert plan.summary_line_limit == 2
    assert plan.skills_line_limit == 4


def test_space_planner_caps_entries_and_bullets_under_large_inventory() -> None:
    plan = SpacePlanner().plan(
        available_experience_entries=1_000,
        available_project_entries=1_000,
        available_education_entries=1_000,
    )

    assert plan.experience.entry_limit == 3
    assert plan.experience.bullets_per_entry_limit == 3
    assert plan.experience.line_limit == 18
    assert plan.projects.entry_limit == 3
    assert plan.projects.bullets_per_entry_limit == 2
    assert plan.projects.line_limit == 18
    assert plan.education.entry_limit == 1
    assert plan.education.bullets_per_entry_limit == 0
    assert plan.education.line_limit == 2


@pytest.mark.parametrize(
    "template_id",
    ["moderncv_two_column_v1", "deedy_cv_v1"],
)
def test_two_column_space_plan_can_retain_complete_verified_inventory(
    template_id: str,
) -> None:
    plan = SpacePlanner().plan(
        available_experience_entries=5,
        available_project_entries=6,
        available_education_entries=1,
        template_id=template_id,
    )

    assert plan.total_line_limit == 56
    assert plan.reserved_line_count == 56
    assert plan.experience.entry_limit == 5
    assert plan.experience.bullets_per_entry_limit == 1
    assert plan.projects.entry_limit == 6
    assert plan.projects.bullets_per_entry_limit == 1


def test_space_planner_never_allocates_entries_that_do_not_exist() -> None:
    plan = SpacePlanner().plan(
        available_experience_entries=1,
        available_project_entries=0,
        available_education_entries=0,
    )

    assert plan.experience.entry_limit == 1
    assert plan.projects.entry_limit == 0
    assert plan.education.entry_limit == 0


@pytest.mark.parametrize(
    (
        "available_experience_entries",
        "available_project_entries",
        "available_education_entries",
    ),
    [(-1, 0, 0), (0, -1, 0), (0, 0, -1)],
)
def test_space_planner_rejects_negative_inventory(
    available_experience_entries: int,
    available_project_entries: int,
    available_education_entries: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=r"^available entry counts must be non-negative$",
    ):
        SpacePlanner().plan(
            available_experience_entries=available_experience_entries,
            available_project_entries=available_project_entries,
            available_education_entries=available_education_entries,
        )


def test_space_policy_rejects_sections_that_exceed_the_page_limit() -> None:
    with pytest.raises(
        ValidationError,
        match="reserved section lines exceed the total line limit",
    ):
        SpacePlanningPolicy(total_line_limit=46)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("experience_entry_limit", 6),
        ("experience_bullets_per_entry_limit", 4),
        ("project_entry_limit", 7),
        ("project_bullets_per_entry_limit", 3),
        ("education_entry_limit", 2),
    ],
)
def test_space_policy_rejects_unreviewed_content_limit_expansion(
    field: str,
    value: int,
) -> None:
    with pytest.raises(ValidationError):
        SpacePlanningPolicy(**{field: value})
