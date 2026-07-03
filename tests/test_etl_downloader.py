"""Unit tests for etl.downloader — MOI bulk zip download and extraction.

Covers Major #3 (Code Review 2026-07-03): `_extract_csv_from_zip` and
`_build_download_url` were previously only exercised indirectly through
`test_etl_pipeline.py`, which mocks the whole downloader module. These tests
exercise the real implementation directly:
    - normal zip → CSV extraction (AC-02)
    - city code URL correctness for 台北市 (A) and 新北市 (F) (AC-02)
    - HTTP 4xx/5xx error propagation (AC-03, TC-13)
    - network-level error propagation (AC-03, TC-13)

httpx.MockTransport is used so no real network call is made and no extra
mocking library is required.
"""

import io
import zipfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import patch

import httpx
import pytest

from etl.downloader import (
    _build_download_url,
    _extract_csv_from_zip,
    download_csv,
)


def _make_zip_bytes(filename: str, content: bytes) -> bytes:
    """Build an in-memory zip archive containing a single file.

    Args:
        filename: Name of the file to store inside the zip.
        content: Raw bytes of the file content.

    Returns:
        Bytes of the resulting zip archive.

    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, content)
    return buf.getvalue()


@asynccontextmanager
async def _client_with_transport(
    transport: httpx.MockTransport,
) -> AsyncIterator[httpx.AsyncClient]:
    """Yield an httpx.AsyncClient wired to a fake transport (no real network).

    Args:
        transport: Pre-configured MockTransport that produces the response.

    Yields:
        httpx.AsyncClient: Client using the given transport.

    """
    async with httpx.AsyncClient(transport=transport) as client:
        yield client


class TestBuildDownloadUrl:
    """Tests for _build_download_url — city code correctness (AC-02)."""

    def test_taipei_city_code(self) -> None:
        """台北市 uses city code 'A' in the download URL."""
        url = _build_download_url("A")
        assert "A_lvr_land_a.zip" in url

    def test_new_taipei_city_code(self) -> None:
        """新北市 uses city code 'F' in the download URL."""
        url = _build_download_url("F")
        assert "F_lvr_land_a.zip" in url

    def test_url_targets_moi_domain(self) -> None:
        """Download URL points at the official MOI open-data endpoint."""
        url = _build_download_url("A")
        assert url.startswith("https://plvr.land.moi.gov.tw/")


class TestExtractCsvFromZip:
    """Tests for _extract_csv_from_zip — normal zip decompression."""

    def test_extracts_matching_csv(self) -> None:
        """Zip containing the target CSV file returns its decoded content."""
        content = "header1,header2\nvalue1,value2\n".encode("utf-8-sig")
        zip_bytes = _make_zip_bytes("A_lvr_land_a.CSV", content)

        result = _extract_csv_from_zip(zip_bytes, "A")

        assert result == content.decode("utf-8-sig")

    def test_no_matching_file_returns_none(self) -> None:
        """Zip without any matching filename returns None instead of raising."""
        zip_bytes = _make_zip_bytes("unrelated.txt", b"irrelevant content")

        result = _extract_csv_from_zip(zip_bytes, "A")

        assert result is None

    def test_case_insensitive_match(self) -> None:
        """Matching is case-insensitive for both the city code and suffix."""
        content = "a,b\n1,2\n".encode("utf-8-sig")
        zip_bytes = _make_zip_bytes("a_lvr_land_a.csv", content)

        result = _extract_csv_from_zip(zip_bytes, "A")

        assert result == content.decode("utf-8-sig")

    def test_extracts_correct_file_among_multiple(self) -> None:
        """The matching file is picked out even when the zip has other entries."""
        target_content = "col1,col2\nval1,val2\n".encode("utf-8-sig")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", b"not csv")
            zf.writestr("F_lvr_land_a.CSV", target_content)
        zip_bytes = buf.getvalue()

        result = _extract_csv_from_zip(zip_bytes, "F")

        assert result == target_content.decode("utf-8-sig")


class TestDownloadCsvHttpErrors:
    """Tests for download_csv HTTP error handling (AC-03, TC-13)."""

    @pytest.mark.asyncio
    async def test_http_4xx_raises_status_error(self) -> None:
        """A 404 response causes download_csv to raise HTTPStatusError."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text="Not Found")

        transport = httpx.MockTransport(handler)

        with patch(
            "etl.downloader._make_http_client",
            return_value=_client_with_transport(transport),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await download_csv("A")

    @pytest.mark.asyncio
    async def test_http_5xx_raises_status_error(self) -> None:
        """A 500 response causes download_csv to raise HTTPStatusError."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        transport = httpx.MockTransport(handler)

        with patch(
            "etl.downloader._make_http_client",
            return_value=_client_with_transport(transport),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await download_csv("F")

    @pytest.mark.asyncio
    async def test_network_error_propagates(self) -> None:
        """A transport-level connection error propagates as httpx.RequestError."""

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        transport = httpx.MockTransport(handler)

        with patch(
            "etl.downloader._make_http_client",
            return_value=_client_with_transport(transport),
        ):
            with pytest.raises(httpx.RequestError):
                await download_csv("A")

    @pytest.mark.asyncio
    async def test_successful_download_extracts_csv(self) -> None:
        """A 200 response with a valid zip body returns the extracted CSV."""
        content = "col1,col2\nval1,val2\n".encode("utf-8-sig")
        zip_bytes = _make_zip_bytes("A_lvr_land_a.CSV", content)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=zip_bytes)

        transport = httpx.MockTransport(handler)

        with patch(
            "etl.downloader._make_http_client",
            return_value=_client_with_transport(transport),
        ):
            result = await download_csv("A")

        assert result == content.decode("utf-8-sig")
