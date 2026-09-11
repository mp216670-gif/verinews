import pytest
from app.services.ingestion.text_adapter import TextIngestionAdapter
from app.services.ingestion.url_scraper import UrlScraperAdapter


@pytest.mark.anyio
async def test_text_ingestion_adapter():
    adapter = TextIngestionAdapter()
    text = (
        "Breaking: Space Agency Announces Manned Lunar Mission for 2028.\n\n"
        "Officials announced today that four astronauts will embark on a historic lunar orbital flight. "
        "The project has undergone rigorous simulation testing according to technical directors."
    )
    results = await adapter.ingest(source=text, publisher="AeroSpace Press", author="Dr. Sarah Cole")
    assert len(results) == 1
    item = results[0]
    assert "Breaking: Space Agency" in item.title
    assert item.publisher == "AeroSpace Press"
    assert item.author == "Dr. Sarah Cole"
    assert len(item.content) > 50


def test_url_scraper_html_parsing():
    scraper = UrlScraperAdapter()
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>New Climate Accord Ratified by 80 Nations - World News</title>
        <meta property="og:title" content="New Climate Accord Ratified by 80 Nations" />
        <meta property="og:site_name" content="Global Dispatch" />
        <meta name="author" content="Elena Vance" />
    </head>
    <body>
        <script>var x = 1;</script>
        <p>In a historic landmark gathering in Geneva, 80 nations officially ratified the sustainable emissions treaty.</p>
        <p>The agreement mandates a 40% reduction in methane emissions over the next decade.</p>
        <p>Short paragraph.</p>
    </body>
    </html>
    """
    title = scraper._extract_title(sample_html)
    assert title == "New Climate Accord Ratified by 80 Nations"

    site_name = scraper._extract_meta(sample_html, "og:site_name")
    assert site_name == "Global Dispatch"

    author = scraper._extract_meta(sample_html, "author")
    assert author == "Elena Vance"

    content = scraper._extract_content(sample_html)
    assert "In a historic landmark" in content
    assert "methane emissions" in content
    assert "var x = 1" not in content
