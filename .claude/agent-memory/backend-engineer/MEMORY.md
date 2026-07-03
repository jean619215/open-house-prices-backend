# Backend Engineer Agent Memory

## Feedback
- [pydantic-settings env file bypass in tests](feedback_pydantic_settings_env_file.md) — Use `Settings(_env_file=None)` to force ValidationError when .env exists on disk
- [Alembic async engine pattern](feedback_alembic_async_engine.md) — asyncio.run + run_sync wrapper required for asyncpg; use Path not os.path (ruff PTH)
- [/health async timeout pattern](feedback_health_check_pattern.md) — asyncio.timeout per probe + gather + redis aclose in finally; AsyncMock engine mock shape
- [ruff Google docstring D413 gotcha](feedback_ruff_google_docstring_d413.md) — blank line required after LAST docstring section, not just first; `--select D413 --fix` is safe but diff-check it
- [verify full TC command checklist before handoff](feedback_verify_full_tc_checklist_before_handoff.md) — run every literal TC command (e.g. `--select D`, `--select ANN`), don't substitute a generic `ruff check .`

## Project Decisions
- [floor field type: VARCHAR(10)](project_floor_field_decision.md) — Raw 實價登錄 strings ('B1','全','頂層') cannot fit SMALLINT; defer numeric parsing to ETL
- [ETL schema field gaps](project_etl_field_gaps.md) — units resolved as m² (not ping); building_type resolved as TEXT; idempotency perf still pending (future TASK); dropped source columns list
- [MOI download URL and zip pattern](project_moi_download_pattern.md) — Returns ZIP not CSV; city code in URL; inner file is utf-8-sig CSV
