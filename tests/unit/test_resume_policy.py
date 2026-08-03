import pytest
from pydantic import ValidationError

from app.models import ResumePolicy


@pytest.mark.unit
def test_resume_policy_requires_exactly_one_page() -> None:
    policy = ResumePolicy(page_count=1)

    assert policy.page_count == 1


@pytest.mark.unit
@pytest.mark.parametrize("page_count", [0, 2, 3])
def test_resume_policy_rejects_any_page_count_other_than_one(page_count: int) -> None:
    with pytest.raises(ValidationError):
        ResumePolicy(page_count=page_count)
