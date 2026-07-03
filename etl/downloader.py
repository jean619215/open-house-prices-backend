"""Downloader for 內政部實價登錄 bulk CSV files.

Downloads and extracts the zipped CSV for each target city using the
official 整批下載 (bulk download) API endpoint.
"""

import io
import logging
import zipfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx

from etl.constants import MOI_DOWNLOAD_BASE_URL, TARGET_CITIES

logger = logging.getLogger(__name__)

# Timeout settings (seconds)
_CONNECT_TIMEOUT: float = 30.0
_READ_TIMEOUT: float = 120.0


@asynccontextmanager
async def _make_http_client() -> AsyncIterator[httpx.AsyncClient]:
    """Create and yield a configured async HTTP client.

    Yields:
        httpx.AsyncClient: Configured client with appropriate timeouts.

    """
    timeout = httpx.Timeout(connect=_CONNECT_TIMEOUT, read=_READ_TIMEOUT, write=30.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        yield client


def _build_download_url(city_code: str) -> str:
    """Build the MOI bulk download URL for a given city code.

    Args:
        city_code: Two-letter city code, e.g. ``"A"`` for 台北市.

    Returns:
        Full download URL string.

    """
    return MOI_DOWNLOAD_BASE_URL.format(city_code=city_code)


def _extract_csv_from_zip(zip_bytes: bytes, city_code: str) -> str | None:
    """Extract the CSV content from a zip archive returned by the MOI API.

    The zip contains multiple files; we target the file ending with
    ``_lvr_land_a.CSV`` (不動產買賣).

    Args:
        zip_bytes: Raw bytes of the downloaded zip file.
        city_code: City code used to identify the target file name, e.g. ``"A"``.

    Returns:
        Decoded CSV string, or ``None`` if no matching file was found.

    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        target_suffix = f"{city_code.lower()}_lvr_land_a.CSV"
        for name in zf.namelist():
            if name.lower().endswith(target_suffix.lower()):
                csv_bytes = zf.read(name)
                logger.info("Extracted %s (%d bytes) from zip", name, len(csv_bytes))
                return csv_bytes.decode("utf-8-sig")
        logger.warning(
            "No matching CSV for city_code=%s in zip (files: %s)",
            city_code,
            zf.namelist(),
        )
        return None


async def download_csv(city_code: str) -> str | None:
    """Download and extract the 不動產買賣 CSV for a given city.

    Args:
        city_code: MOI city code, e.g. ``"A"`` (台北市) or ``"F"`` (新北市).

    Returns:
        Raw CSV string content, or ``None`` if download or extraction failed.

    Raises:
        httpx.HTTPStatusError: If the server returns an HTTP error (4xx/5xx).
        httpx.RequestError: If a network-level error occurs.

    """
    url = _build_download_url(city_code)
    city_name = TARGET_CITIES.get(city_code, city_code)
    logger.info("Downloading %s (%s) from %s", city_name, city_code, url)

    async with _make_http_client() as client:
        response = await client.get(url)
        response.raise_for_status()

    logger.info(
        "Downloaded %s: HTTP %d, %d bytes",
        city_name,
        response.status_code,
        len(response.content),
    )
    return _extract_csv_from_zip(response.content, city_code)


async def download_all_target_cities() -> dict[str, str]:
    """Download CSVs for all target cities (台北市 + 新北市).

    Returns:
        Mapping of city_code → CSV string for successfully downloaded cities.

    Raises:
        httpx.HTTPStatusError: If any download returns an HTTP error.
        httpx.RequestError: If a network error occurs for any city.

    """
    results: dict[str, str] = {}
    for city_code in TARGET_CITIES:
        csv_content = await download_csv(city_code)
        if csv_content is not None:
            results[city_code] = csv_content
        else:
            logger.warning("No CSV content retrieved for city_code=%s", city_code)
    return results


def save_csv_to_disk(content: str, path: Path) -> None:
    """Write CSV content to a file on disk (helper for debugging).

    Args:
        content: CSV string content.
        path: Target file path.

    """
    path.write_text(content, encoding="utf-8")
    logger.debug("Saved CSV to %s", path)
