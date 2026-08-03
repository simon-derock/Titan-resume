"""Validated domain models for TITAN."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ResumePolicy(BaseModel):
    """Hard document constraints that cannot be relaxed by repair logic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    page_count: Literal[1] = 1
