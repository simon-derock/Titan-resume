import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.mark.unit
def test_settings_require_admin_telegram_id() -> None:
    with pytest.raises(ValidationError):
        Settings(admin_telegram_ids=set())
