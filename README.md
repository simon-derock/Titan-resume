# TITAN — Self-Correcting AI Resume Compiler

TITAN is an evidence-grounded resume compiler that targets a truthful,
ATS-readable, exactly one-page PDF. The project is being built incrementally
under the test-driven contract in [`TITAN_PLAN.md`](TITAN_PLAN.md).

## Development

```bash
uv sync --extra dev
uv run pytest -m "not live_llm and not live_vision" -q
```

The deterministic vertical slice is the first implementation milestone; live
model and Telegram integrations are intentionally deferred until its quality
gates pass.

