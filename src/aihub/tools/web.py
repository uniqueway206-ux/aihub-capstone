"""Web page + YouTube summarisation and web search (Module 4/5: agents & tools).

Includes an SSRF guard: only public http(s) hosts are fetched.
"""
import ipaddress
import logging
import re
import socket
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from ..errors import UnsafeURLError, UpstreamError, ValidationError
from ..llm import text_of

log = logging.getLogger(__name__)
MAX_BYTES = 2_000_000
CHUNK_CHARS = 8000


def assert_public_url(url: str) -> str:
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise UnsafeURLError("Only http(s) URLs are allowed.")
    try:
        infos = socket.getaddrinfo(p.hostname, None)
    except socket.gaierror as e:
        raise ValidationError(f"Cannot resolve host: {p.hostname}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise UnsafeURLError("URL resolves to a non-public address.")
    return url


def youtube_id(url: str) -> str | None:
    p = urlparse(url)
    host = (p.hostname or "").removeprefix("www.")
    if host == "youtu.be":
        return p.path.lstrip("/") or None
    if host in ("youtube.com", "m.youtube.com"):
        if p.path == "/watch":
            return parse_qs(p.query).get("v", [None])[0]
        m = re.match(r"^/(?:shorts|embed)/([\w-]{6,})", p.path)
        return m.group(1) if m else None
    return None


def fetch_page_text(url: str) -> str:
    assert_public_url(url)
    try:
        r = requests.get(
            url, timeout=15, stream=True, headers={"User-Agent": "AIHub/1.0"}, allow_redirects=False
        )
        if 300 <= r.status_code < 400:
            raise UnsafeURLError("Redirects are not followed; paste the final URL.")
        r.raise_for_status()
        raw = r.raw.read(MAX_BYTES, decode_content=True)
    except requests.RequestException as e:
        raise UpstreamError(f"Could not fetch page: {e}") from e
    soup = BeautifulSoup(raw, "html.parser")
    for t in soup(["script", "style", "nav", "footer", "header", "aside"]):
        t.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def fetch_youtube_transcript(video_id: str) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            parts = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join(p["text"] for p in parts)
        return " ".join(s.text for s in YouTubeTranscriptApi().fetch(video_id))
    except Exception as e:  # library raises many specific types
        raise UpstreamError(f"Transcript unavailable for this video: {e}") from e


def summarize_text(llm, content: str) -> str:
    """Map-reduce summarisation so long inputs fit the context window."""
    if not content.strip():
        raise ValidationError("Nothing to summarise.")
    chunks = [content[i : i + CHUNK_CHARS] for i in range(0, len(content), CHUNK_CHARS)][:12]
    partials = [
        text_of(llm.invoke(f"Summarise the key points of this text in 4-6 bullets:\n\n{c}"))
        for c in chunks
    ]
    if len(partials) == 1:
        return partials[0]
    joined = "\n\n".join(partials)
    return text_of(
        llm.invoke(f"Combine these partial summaries into one clear, concise summary:\n\n{joined}")
    )


def summarize_url(llm, url: str) -> dict:
    vid = youtube_id(url)
    if vid:
        content, kind = fetch_youtube_transcript(vid), "youtube"
    else:
        content, kind = fetch_page_text(url), "webpage"
    return {"summary": summarize_text(llm, content), "type": kind, "url": url}


def web_search(query: str, max_results: int = 5) -> list[dict]:
    try:
        try:
            from ddgs import DDGS
        except ImportError:  # older package name
            from duckduckgo_search import DDGS
        return [
            {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
            for r in DDGS().text(query, max_results=max_results)
        ]
    except Exception as e:
        raise UpstreamError(f"Web search failed: {e}") from e
