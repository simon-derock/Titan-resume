"""Tests for Telegram bot service authentication, command handling, and execution routing."""

from datetime import date
from pathlib import Path
import pytest

from app.config import Settings
from app.models import (
    CompileResult,
    DeterministicPipelineResult,
    EvidenceRecord,
    PdfValidationReport,
    ResumeHeader,
)
from app.services.telegram import (
    TelegramBotService,
    TelegramUpdate,
)


class FakeExecutor:
    """Stub executor for test isolation."""

    def __init__(self, status: str = "passed", pdf_path: Path | None = None) -> None:
        self._status = status
        self._pdf_path = pdf_path or Path("/tmp/resume.pdf")

    def run(
        self,
        *,
        raw_jd_text: str,
        header: ResumeHeader,
        evidence_records: tuple[EvidenceRecord, ...],
        output_dir: Path,
        template_id: str = "resume_v1",
    ) -> dict:
        compile_result = CompileResult(
            success=True,
            exit_code=0,
            pdf_path=str(self._pdf_path),
            log="Success",
        )
        pipeline_result = DeterministicPipelineResult(
            status="passed" if self._status == "passed" else "validation_failed",
            passed=(self._status == "passed"),
            pdf_path=str(self._pdf_path),
            tex_path=str(self._pdf_path.with_suffix(".tex")),
            compile_result=compile_result,
            page_report=PdfValidationReport(passed=True, page_count=1),
        )
        return {
            "status": self._status,
            "pipeline_result": pipeline_result,
            "repair_feedback": None,
        }


def test_telegram_rejects_unauthorized_user() -> None:
    """Users not present in admin_telegram_ids must be rejected immediately."""
    settings = Settings(admin_telegram_ids=frozenset({123456789}))
    service = TelegramBotService(settings=settings)
    update = TelegramUpdate(update_id=1, user_id=999999999, chat_id=100, text="Hello")

    response = service.handle_update(update)

    assert response.authorized is False
    assert "Unauthorized" in response.text


def test_telegram_handles_start_command() -> None:
    """Authorized users issuing /start receive service introduction and commands."""
    settings = Settings(admin_telegram_ids=frozenset({123456789}))
    service = TelegramBotService(settings=settings)
    update = TelegramUpdate(update_id=1, user_id=123456789, chat_id=100, text="/start")

    response = service.handle_update(update)

    assert response.authorized is True
    assert "TITAN" in response.text
    assert "/start" in response.text or "/help" in response.text


def test_telegram_processes_jd_with_executor(tmp_path: Path) -> None:
    """Valid JD text triggers graph execution and returns PDF path."""
    settings = Settings(admin_telegram_ids=frozenset({123456789}))
    pdf_path = tmp_path / "resume.pdf"
    executor = FakeExecutor(status="passed", pdf_path=pdf_path)
    header = ResumeHeader(
        name="Simon Derock",
        headline="AI Engineer",
        email="simon@example.com",
        phone="+1-555-0199",
        location="San Francisco, CA",
    )
    service = TelegramBotService(
        settings=settings,
        executor=executor,
        header=header,
        output_dir=tmp_path,
    )

    jd_text = "Senior AI Engineer — PyTorch, FastAPI, Pydantic, LLM workflows"
    update = TelegramUpdate(update_id=1, user_id=123456789, chat_id=100, text=jd_text)

    response = service.handle_update(update)

    assert response.authorized is True
    assert response.pdf_path == pdf_path
    assert "✅" in response.text or "Passed" in response.text
