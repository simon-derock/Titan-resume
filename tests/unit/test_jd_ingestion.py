import hashlib

import pytest

from app.services.jd import JobDescriptionIngester, JobDescriptionIngestionError


def ingester() -> JobDescriptionIngester:
    return JobDescriptionIngester(minimum_characters=20, maximum_characters=1_000)


@pytest.mark.parametrize(
    ("minimum_characters", "maximum_characters", "message"),
    [
        (0, 100, "minimum_characters must be positive"),
        (100, 99, "maximum_characters must not be smaller than the minimum"),
    ],
)
def test_jd_ingestion_rejects_invalid_size_policy(
    minimum_characters: int,
    maximum_characters: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=f"^{message}$"):
        JobDescriptionIngester(
            minimum_characters=minimum_characters,
            maximum_characters=maximum_characters,
        )


@pytest.mark.parametrize("raw_text", ["", "   \n\t ", "AI Engineer"])
def test_jd_ingestion_rejects_empty_or_extremely_short_input(raw_text: str) -> None:
    with pytest.raises(
        JobDescriptionIngestionError,
        match=r"^job description is too short$",
    ):
        ingester().ingest(raw_text)


def test_jd_ingestion_rejects_oversized_input() -> None:
    with pytest.raises(
        JobDescriptionIngestionError,
        match=r"^job description exceeds the size limit$",
    ):
        ingester().ingest("Python " * 200)


def test_jd_ingestion_normalizes_whitespace_and_removes_duplicate_blocks() -> None:
    raw_text = """
      AI Engineer\r
      Build reliable RAG systems.  \n
      Requirements
      Python   and LangGraph

      Requirements
      Python and LangGraph
    """

    document = ingester().ingest(raw_text)

    assert document.raw_text == (
        "AI Engineer\nBuild reliable RAG systems.\n\nRequirements\nPython and LangGraph"
    )


def test_jd_ingestion_hashes_the_normalized_content() -> None:
    first = ingester().ingest("AI Engineer\n\nBuild reliable RAG systems")
    second = ingester().ingest(
        "  AI   Engineer  \r\n\r\n  Build reliable   RAG systems  "
    )

    expected_hash = hashlib.sha256(first.raw_text.encode()).hexdigest()
    assert first.raw_text_hash == expected_hash
    assert second.raw_text_hash == expected_hash
