"""CLI entry point for the 實價登錄 ETL pipeline.

Usage:
    python -m etl.run

Exits with code 0 on success, non-zero on download or unexpected errors.
"""

import asyncio
import logging
import sys

import httpx

from etl.pipeline import run_pipeline

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the ETL pipeline and exit with an appropriate exit code.

    Raises:
        SystemExit: Always exits; code 0 on success, 1 on error.

    """
    try:
        asyncio.run(run_pipeline())
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.error("ETL pipeline 中止：下載失敗 — %s", exc)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        logger.error("ETL pipeline 中止：未預期錯誤 — %s", exc, exc_info=True)
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
