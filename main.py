import logging
import os
import re
import uuid
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv
from fake_useragent import UserAgent

from config import AppSettings
from database import add_hash, hash_exists, setup_database
from logger import setup_logging
from utils import get_pdf_hash

logger = logging.getLogger(__name__)


SCHEDULE_72HR_REGEX = [re.compile(r"72hr", re.IGNORECASE)]

HEADERS = {
    "User-Agent": UserAgent().chrome,
    "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def get_pdf_links(url: str, **kwargs: Any) -> list[str]:
    """Get all PDFs URLs on the page.

    Args:
    ----
        url (str): The URL to scrape.
        kwargs (Any)): Additional keyword arguements.
        headers (dict[str, Any]): Headers to include in request to URL.

    Returns:
    -------
        list[str]: List of PDF links found on the page.

    """
    logger.info("Attempting to scrape PDF links from: %s", url)
    pdf_links: list[str] = []
    logger.info("using headers: %s", kwargs["headers"])

    try:
        # Fetch the web page
        response = httpx.get(url, **kwargs)
        response.raise_for_status()

        logger.info(
            "Successfully fetched the page. Status code: %s", response.status_code
        )

        # Parse response
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all 'a' tags that have an 'href' attribute.
        for link in soup.find_all("a", href=True):

            if not isinstance(link, Tag):
                continue

            href = link.get("href")

            if not isinstance(href, str):
                continue

            path = urlparse(href).path
            if path.endswith(".pdf"):
                absolute_url = urljoin(url, href)
                pdf_links.append(absolute_url)
                logger.debug("Found PDF at: %s", absolute_url)

        logger.info("Found %s PDF link(s) on: %s", len(pdf_links), url)

    except httpx.RequestError as e:
        logger.error("An error occurred while requesting '%s'.", e.request.url)
        logger.error("Error details: %s", e)
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP Error %s %s for '%s'.",
            e.response.status_code,
            e.response.reason_phrase,
            e.request.url,
        )
    except Exception as e:
        logger.critical(
            "An unexpected and critical error occurred: %e", e, exc_info=True
        )

    return pdf_links


def download_pdf(url: str, save_path: str, **kwargs: Any) -> str | None:
    """Download PDF to local filesystem.

    Args:
    ----
        url (str): URL to PDF.
        save_path (str): Local file path to save PDF.
        kwargs (dict[str, Any]): Additional keyword arguements.
        headers (dict[str, Any]): Headers to include in request to URL.

    Returns:
    -------
        str | None: Path of downloaded file.

    """
    logger.info("Starting download of PDF from: %s", url)
    logger.info("using headers: %s", kwargs["headers"])

    try:
        with httpx.stream(
            "GET", url, follow_redirects=True, timeout=30.0, **kwargs
        ) as response:
            response.raise_for_status()

            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # Save PDF
            with open(save_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)

            logger.info("Successfully saved PDF to: %s", save_path)
            return save_path

    except httpx.RequestError as e:
        logger.error("An error occurred while downloading PDF: %s", e.request.url)
        logger.error("Error details: %s", e)
        return None
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP Error %s %s while downloading PDF: %s",
            e.response.status_code,
            e.response.reason_phrase,
            e.request.url,
        )
        return None
    except Exception as e:
        logger.critical(
            "An unexpected and critical error occurred while download PDF: %e",
            e,
            exc_info=True,
        )
        return None


def filter_list(data: list[str], patterns: list[re.Pattern[str]]) -> list[str]:
    """Return list of strings that match any of the patterns in filters.

    Args:
    ----
        data (list[str]): List of strings to filter.
        patterns (list[re.Pattern[str]]): List of compiled string regex patterns.

    Returns:
    -------
        list[str]: List of strings that match any of the patterns.

    """
    return [text for text in data if any(pattern.search(text) for pattern in patterns)]


if __name__ == "__main__":
    # App startup sequence
    setup_logging()

    if not load_dotenv():
        logger.info("No ENV file found.")

    setup_database()

    os.makedirs(AppSettings.DOWNLOAD_DIR.value, exist_ok=True)

    # Scrape
    target_url = "https://www.amc.af.mil/AMC-Travel-Site/Terminals/CONUS-Terminals/Baltimore-Washington-International-Airport-Passenger-Terminal/"
    HEADERS["Referer"] = f"https://{urlparse(target_url).hostname}"

    pdf_links = get_pdf_links(target_url, headers=HEADERS)
    pdf_72hr_links = filter_list(pdf_links, SCHEDULE_72HR_REGEX)

    pdfs_72hrs = [
        download_pdf(
            pdf_link,
            f"{AppSettings.DOWNLOAD_DIR.value}/{uuid.uuid4()}.pdf",
            headers=HEADERS,
        )
        for pdf_link in pdf_72hr_links
    ]

    # Store PDFs
    for pdf_path, pdf_url in zip(pdfs_72hrs, pdf_72hr_links, strict=True):
        if not pdf_path:
            continue

        with open(pdf_path, mode="rb") as file:
            pdf_bytes = file.read()

        pdf_hash = get_pdf_hash(pdf_bytes)

        if not hash_exists(pdf_hash):
            add_hash(pdf_hash, pdf_url)
            logger.info("New 72HR schedule PDF found! Saving to database...")
        else:
            logger.info("72HR schedule seen before. Hash: %s", pdf_hash)
