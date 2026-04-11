import io
import os
import re

import requests
from agents import function_tool
from PyPDF2 import PdfReader


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _extract_doi(url: str) -> str | None:
    """Extract DOI from a biorxiv URL."""
    match = re.search(r"10\.\d{4,9}/[^\s]+", url)
    if match:
        return match.group(0).rstrip("/").split("v")[0]
    return None


def _fetch_via_api(doi: str) -> str:
    """Fetch paper content via biorxiv API (abstract + metadata)."""
    api_url = f"https://api.biorxiv.org/details/biorxiv/{doi}"
    response = requests.get(api_url, timeout=30)
    response.raise_for_status()

    data = response.json()
    if not data.get("collection"):
        raise ValueError(f"No results found for DOI: {doi}")

    paper = data["collection"][0]
    parts = [
        f"Title: {paper.get('title', 'N/A')}",
        f"Authors: {paper.get('authors', 'N/A')}",
        f"Institution: {paper.get('author_corresponding_institution', 'N/A')}",
        f"Date: {paper.get('date', 'N/A')}",
        f"Category: {paper.get('category', 'N/A')}",
        f"DOI: {paper.get('doi', 'N/A')}",
        f"\nAbstract:\n{paper.get('abstract', 'N/A')}",
    ]
    return "\n".join(parts)


def _read_pdf(source: io.BytesIO | str) -> str:
    """Extract text from a PDF (file path or bytes buffer)."""
    reader = PdfReader(source)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    full_text = "\n\n".join(pages)
    if not full_text.strip():
        raise ValueError("PDF contained no extractable text")

    return full_text


def _fetch_pdf(url: str) -> str:
    """Download and extract text from a PDF URL."""
    if "biorxiv.org" in url and not url.endswith(".pdf"):
        url = url.rstrip("/") + ".full.pdf"

    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()

    return _read_pdf(io.BytesIO(response.content))


@function_tool
def download_and_read_paper(url: str) -> str:
    """Read a research paper and extract its text content.

    Accepts a local file path or a URL. For URLs, tries PDF download first.
    If blocked (e.g. by Cloudflare), falls back to the biorxiv API for
    abstract and metadata only.

    Limitations:
    - Biorxiv PDFs are often blocked by Cloudflare, triggering the API fallback.
    - PDF text extraction is text-only (no images, figures, or tables as images).
    - When the API fallback is used, only abstract and metadata are returned.

    Args:
        url: Local file path to a PDF, or a URL of the paper.
    """
    # Local file
    if os.path.isfile(url):
        return _read_pdf(url)

    # Remote URL — try PDF download first
    try:
        full_text = _fetch_pdf(url)
    except Exception:
        # Fallback to biorxiv API if it's a biorxiv paper
        doi = _extract_doi(url)
        if doi:
            full_text = (
                "[Note: Full PDF was not accessible. Content below is from the biorxiv API "
                "(abstract and metadata only).]\n\n"
                + _fetch_via_api(doi)
            )
        else:
            raise

    return full_text
