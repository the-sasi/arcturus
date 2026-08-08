import pytest

from arcturus_api.domain.market.errors import ArticleFetchError
from arcturus_api.infrastructure.readers.trafilatura_reader import (
    extract_article,
    validate_public_http_url,
)

ARTICLE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>RIL hits record high | Example News</title>
  <meta property="og:title" content="RIL hits record high" />
  <meta property="og:image" content="https://cdn.example.com/ril.jpg" />
  <meta property="og:site_name" content="Example News" />
</head>
<body>
  <article>
    <h1>RIL hits record high</h1>
    <p>Reliance Industries shares rose to a record on Friday after the company
    announced stronger than expected quarterly results, led by growth in its
    retail and digital services businesses.</p>
    <p>Analysts said the momentum could continue into the next quarter given
    steady refining margins and subscriber additions.</p>
  </article>
</body>
</html>
"""


class TestUrlValidation:
    def test_https_public_ok(self) -> None:
        validate_public_http_url("https://www.reuters.com/some/article")

    @pytest.mark.parametrize(
        "url",
        [
            "ftp://example.com/file",
            "file:///etc/passwd",
            "https://localhost/x",
            "http://127.0.0.1/x",
            "http://10.0.0.5/internal",
            "http://192.168.1.1/router",
            "https://[::1]/x",
        ],
    )
    def test_non_public_rejected(self, url: str) -> None:
        with pytest.raises(ArticleFetchError):
            validate_public_http_url(url)


class TestExtractArticle:
    def test_extracts_text_and_metadata(self) -> None:
        content = extract_article("https://news.example.com/ril", ARTICLE_HTML)
        assert content.text is not None
        assert "record" in content.text.lower()
        assert content.title == "RIL hits record high"
        assert content.image_url == "https://cdn.example.com/ril.jpg"
        assert content.site_name is not None

    def test_empty_page_yields_no_text(self) -> None:
        content = extract_article("https://news.example.com/empty", "<html><body></body></html>")
        assert content.text is None
