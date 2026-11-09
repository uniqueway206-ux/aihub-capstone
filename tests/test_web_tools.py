import pytest

from aihub.errors import UnsafeURLError
from aihub.tools.web import assert_public_url, youtube_id


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "ftp://example.com", "http://127.0.0.1/admin",
    "http://localhost:8000", "http://169.254.169.254/latest/meta-data",
])
def test_ssrf_blocked(url):
    with pytest.raises(UnsafeURLError):
        assert_public_url(url)


def test_youtube_id_parsing():
    assert youtube_id("https://www.youtube.com/watch?v=abc123XYZ") == "abc123XYZ"
    assert youtube_id("https://youtu.be/abc123XYZ") == "abc123XYZ"
    assert youtube_id("https://www.youtube.com/shorts/abc123XYZ") == "abc123XYZ"
    assert youtube_id("https://example.com/watch?v=1") is None
