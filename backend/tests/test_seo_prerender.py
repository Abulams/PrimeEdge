import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_homepage_seo_prerender():
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    # Route-specific title & canonical
    assert "PrimeEdge | Evidence-Based Trading Decisions & Risk Control" in html
    assert '<link rel="canonical" href="https://primeedge.app/" />' in html
    assert '<meta name="description" content="PrimeEdge helps intraday FX and gold traders evaluate setups with historical evidence, plan risk-aware entries and journal every decision before execution." />' in html
    # Open Graph & Twitter
    assert '<meta property="og:title" content="PrimeEdge | Evidence-Based Trading Decisions & Risk Control" />' in html
    assert '<meta property="og:description" content="PrimeEdge helps intraday FX and gold traders evaluate setups with historical evidence, plan risk-aware entries and journal every decision before execution." />' in html
    assert '<meta name="twitter:card" content="summary_large_image" />' in html
    # Semantic crawler-visible HTML (H1 and opening copy)
    assert "Turn Trading Setups Into Evidence-Based Decisions." in html
    assert "PrimeEdge helps intraday FX and gold traders evaluate setups with historical evidence, define risk-aware entry and invalidation zones, replay past conditions and record every decision before execution." in html
    assert "P25–P75 Entry Corridor" in html
    assert "Historical Replay Engine" in html
    # Structured Data
    assert '"@type": "SoftwareApplication"' in html
    assert "Evidence-based trading decision-support software for intraday FX and gold traders, combining setup evaluation, historical replay, risk-aware trade planning, automated journaling and execution controls." in html

def test_pricing_seo_prerender():
    response = client.get("/pricing")
    assert response.status_code == 200
    html = response.text
    assert "PrimeEdge Pricing | Trading Intelligence, Replay & Execution Plans" in html
    assert '<link rel="canonical" href="https://primeedge.app/pricing" />' in html
    assert "PrimeEdge Plans &amp; Pricing" in html
    assert "$79" in html
    assert "$199" in html

def test_robots_txt():
    response = client.get("/robots.txt")
    assert response.status_code == 200
    text = response.text
    assert "Disallow: /login" in text
    assert "Disallow: /register" in text
    assert "Sitemap: https://primeedge.app/sitemap.xml" in text

def test_sitemap_xml():
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    xml = response.text
    assert "https://primeedge.app/" in xml
    assert "https://primeedge.app/pricing" in xml
    assert "https://primeedge.app/terms" in xml
    assert "https://primeedge.app/privacy" in xml
    # /login MUST NOT be in sitemap
    assert "/login" not in xml

def test_login_noindex():
    response = client.get("/login")
    assert response.status_code == 200
    html = response.text
    assert '<meta name="robots" content="noindex, follow" />' in html

def test_real_404_for_unknown_routes():
    response = client.get("/not-a-real-page-random-xyz")
    assert response.status_code == 404
    html = response.text
    assert "Page Not Found" in html
    assert '<meta name="robots" content="noindex, follow" />' in html
