"""Telegram Bot Service for private admin authorization, JD ingestion, and status reporting."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from app.config import Settings
from app.models import EvidenceRecord, ResumeHeader

if TYPE_CHECKING:
    from app.graph import ResumeGraphExecutor


class TelegramUpdate(BaseModel):
    """Inbound update representation from Telegram webhook or long-polling."""

    model_config = ConfigDict(frozen=True)

    update_id: int
    user_id: int
    chat_id: int
    text: str | None = None
    document_file_id: str | None = None


class TelegramResponse(BaseModel):
    """Outbound response payload to be dispatched to Telegram chat."""

    model_config = ConfigDict(frozen=True)

    authorized: bool
    chat_id: int
    text: str
    pdf_path: Path | None = None


class TelegramBotService:
    """Private service handling Telegram authorization and graph orchestration."""

    def __init__(
        self,
        *,
        settings: Settings,
        executor: ResumeGraphExecutor | None = None,
        header: ResumeHeader | None = None,
        evidence_records: tuple[EvidenceRecord, ...] = (),
        output_dir: Path | None = None,
    ) -> None:
        self._settings = settings
        self._executor = executor
        self._header = header
        self._evidence_records = evidence_records
        self._output_dir = output_dir or Path("outputs")

    def is_authorized(self, user_id: int) -> bool:
        """Return True if user_id is in the admin_telegram_ids allowlist."""
        return user_id in self._settings.admin_telegram_ids

    def handle_update(self, update: TelegramUpdate) -> TelegramResponse:
        """Process inbound update and return structured response payload."""
        if not self.is_authorized(update.user_id):
            return TelegramResponse(
                authorized=False,
                chat_id=update.chat_id,
                text="Unauthorized access denied. This TITAN bot instance is private.",
            )

        text = (update.text or "").strip()

        if text.startswith("/start") or text.startswith("/help"):
            return TelegramResponse(
                authorized=True,
                chat_id=update.chat_id,
                text=(
                    "Welcome to TITAN — Self-Correcting AI Resume Compiler.\n\n"
                    "Available Commands:\n"
                    "/start - Show introduction and menu\n"
                    "/help  - Display usage guide\n\n"
                    "To generate a tailored 1-page resume, send the Job Description text directly to this chat."
                ),
            )

        if self._executor and self._header and len(text) >= 20:
            state = self._executor.run(
                raw_jd_text=text,
                header=self._header,
                evidence_records=self._evidence_records,
                output_dir=self._output_dir,
            )
            status = state.get("status", "unknown")
            pipeline_result = state.get("pipeline_result")
            raw_pdf_path = pipeline_result.pdf_path if pipeline_result else None
            pdf_path = Path(raw_pdf_path) if raw_pdf_path else None

            if status == "passed" and pdf_path:
                msg = (
                    "✅ Resume Generation Passed All Deterministic Gates!\n\n"
                    f"PDF Path: {pdf_path.name}\n"
                    "Page Count: 1 (Verified)\n"
                    "ATS Reading Order: Validated"
                )
                return TelegramResponse(
                    authorized=True,
                    chat_id=update.chat_id,
                    text=msg,
                    pdf_path=pdf_path,
                )

            feedback = state.get("repair_feedback") or "Execution halted."
            return TelegramResponse(
                authorized=True,
                chat_id=update.chat_id,
                text=f"⚠️ Resume generation completed with status: {status}\n\nFeedback: {feedback}",
                pdf_path=pdf_path,
            )

        return TelegramResponse(
            authorized=True,
            chat_id=update.chat_id,
            text=f"Received input ({len(text)} chars). Ready to process.",
        )
