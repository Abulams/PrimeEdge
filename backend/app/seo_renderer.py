"""
PrimeEdge SEO Prerendering & Route Metadata Engine.

Provides crawler-visible semantic HTML, route-specific metadata,
canonical URL alignment (https://primeedge.app), structured JSON-LD data,
and eliminates soft-404 errors by serving strict HTTP 404s for unknown routes.
"""

from typing import Dict, Any, Optional

CANONICAL_DOMAIN = "https://primeedge.app"

VALID_SPA_ROUTES = {
    "",
    "/",
    "/pricing",
    "/login",
    "/register",
    "/signup",
    "/terms",
    "/privacy",
    "/waitlist",
    "/app",
    "/dashboard",
    "/admin",
    "/cockpit",
    "/journal",
    "/copier",
    "/replay",
    "/settings",
    "/subscription",
    "/forgot-password",
    "/reset-password",
    "/forgot",
    "/reset",
}

# ---------------------------------------------------------------------------
# Structured Data Schemas
# ---------------------------------------------------------------------------

HOMEPAGE_JSON_LD = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "Organization",
            "@id": f"{CANONICAL_DOMAIN}/#organization",
            "name": "PrimeEdge",
            "url": CANONICAL_DOMAIN,
            "logo": f"{CANONICAL_DOMAIN}/market_os_logo_emblem.jpg",
            "description": "Evidence-based trading decision support, setup evaluation, and automated risk guardrails for intraday traders.",
            "sameAs": []
        },
        {
            "@type": "WebSite",
            "@id": f"{CANONICAL_DOMAIN}/#website",
            "url": CANONICAL_DOMAIN,
            "name": "PrimeEdge",
            "publisher": {
                "@id": f"{CANONICAL_DOMAIN}/#organization"
            }
        },
        {
            "@type": "SoftwareApplication",
            "@id": f"{CANONICAL_DOMAIN}/#software",
            "name": "PrimeEdge",
            "applicationCategory": "FinanceApplication",
            "operatingSystem": "Web, Windows, macOS, Linux",
            "url": CANONICAL_DOMAIN,
            "description": "Evidence-based trading decision-support software for intraday FX and gold traders, combining setup evaluation, historical replay, risk-aware trade planning, automated journaling and execution controls.",
            "offers": {
                "@type": "AggregateOffer",
                "priceCurrency": "USD",
                "lowPrice": "0",
                "highPrice": "199",
                "offerCount": "3",
                "offers": [
                    {
                        "@type": "Offer",
                        "name": "Starter",
                        "price": "0",
                        "priceCurrency": "USD",
                        "description": "Setup discovery, macro regime decomposition, and historical corridor analysis."
                    },
                    {
                        "@type": "Offer",
                        "name": "Pro",
                        "price": "79",
                        "priceCurrency": "USD",
                        "description": "Trade planner, historical replay engine, and automated execution guardrails."
                    },
                    {
                        "@type": "Offer",
                        "name": "Premium",
                        "price": "199",
                        "priceCurrency": "USD",
                        "description": "Automated execution controls, multi-account allocation, and priority support."
                    }
                ]
            }
        }
    ]
}

PRICING_JSON_LD = {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "PrimeEdge Trading Decision & Execution Platform",
    "description": "Subscription plans for evidence-based setup discovery, historical replay, automated trade journal, and execution risk guardrails.",
    "brand": {
        "@type": "Brand",
        "name": "PrimeEdge"
    },
    "offers": {
        "@type": "AggregateOffer",
        "priceCurrency": "USD",
        "lowPrice": "0",
        "highPrice": "199",
        "offerCount": "3"
    }
}

# ---------------------------------------------------------------------------
# Semantic Crawler-Visible Prerendered HTML
# ---------------------------------------------------------------------------

HOMEPAGE_CRAWLER_HTML = """
<div class="prerender-shell" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #07090e; color: #f0f4f8; min-height: 100vh; padding: 2rem 1.5rem; max-width: 1200px; margin: 0 auto; line-height: 1.6;">
  <header style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 2rem; border-bottom: 1px solid rgba(255,255,255,0.08);">
    <div style="font-size: 1.5rem; font-weight: 700; color: #00e5ff; letter-spacing: -0.5px;">PrimeEdge</div>
    <nav style="display: flex; gap: 1.5rem; font-size: 0.95rem;">
      <a href="/pricing" style="color: #94a3b8; text-decoration: none;">Pricing</a>
      <a href="/terms" style="color: #94a3b8; text-decoration: none;">Risk Disclosure</a>
      <a href="/privacy" style="color: #94a3b8; text-decoration: none;">Privacy</a>
      <a href="/login" style="color: #00e5ff; text-decoration: none; font-weight: 600;">Sign In</a>
    </nav>
  </header>

  <main style="padding: 4rem 0 3rem 0;">
    <div style="max-width: 820px;">
      <div style="display: inline-block; padding: 0.35rem 0.85rem; background: rgba(0,229,255,0.1); border: 1px solid rgba(0,229,255,0.25); border-radius: 9999px; font-size: 0.82rem; color: #00e5ff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 1.5rem;">
        Decision Support for Intraday Traders
      </div>
      <h1 style="font-size: 2.75rem; line-height: 1.2; font-weight: 800; color: #ffffff; letter-spacing: -0.03em; margin: 0 0 1.5rem 0;">
        Turn Trading Setups Into Evidence-Based Decisions.
      </h1>
      <p style="font-size: 1.2rem; color: #94a3b8; margin: 0 0 2.5rem 0;">
        PrimeEdge helps intraday FX and gold traders evaluate setups with historical evidence, define risk-aware entry and invalidation zones, replay past conditions and record every decision before execution.
      </p>
      <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 3.5rem;">
        <a href="/pricing" style="display: inline-block; background: #00e5ff; color: #07090e; font-weight: 700; padding: 0.9rem 1.8rem; border-radius: 6px; text-decoration: none; font-size: 1rem;">View Plans &amp; Pricing</a>
        <a href="/register" style="display: inline-block; background: rgba(255,255,255,0.06); color: #ffffff; font-weight: 600; padding: 0.9rem 1.8rem; border-radius: 6px; text-decoration: none; font-size: 1rem; border: 1px solid rgba(255,255,255,0.12);">Get Started with Starter</a>
      </div>
    </div>

    <section style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; margin-top: 3rem;">
      <article style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 2rem;">
        <h2 style="font-size: 1.25rem; font-weight: 700; color: #00e5ff; margin-top: 0;">Statistical Setup Evaluation</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 0;">
          Every setup is benchmarked against its specific Macro Regime, Market State Score (MSS), and historical Maximum Adverse Excursion (MAE) / Maximum Favorable Excursion (MFE) distributions.
        </p>
      </article>

      <article style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 2rem;">
        <h2 style="font-size: 1.25rem; font-weight: 700; color: #00e5ff; margin-top: 0;">P25–P75 Entry Corridor</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 0;">
          Avoid chasing price or buying at arbitrary levels. PrimeEdge calculates the empirical retracement corridor (P25 to P75) where historically valid setups optimal risk-adjusted entries occur.
        </p>
      </article>

      <article style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 2rem;">
        <h2 style="font-size: 1.25rem; font-weight: 700; color: #00e5ff; margin-top: 0;">-0.35R Early Invalidation Guardrail</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 0;">
          Protect capital before full stop-loss hits. When adverse excursion crosses statistical boundary thresholds, PrimeEdge triggers early invalidation alerts to minimize drawdown.
        </p>
      </article>

      <article style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 2rem;">
        <h2 style="font-size: 1.25rem; font-weight: 700; color: #00e5ff; margin-top: 0;">Historical Replay Engine</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 0;">
          Test your decision discipline across thousands of past market sessions without risking capital. Replay tick-by-tick setups and evaluate execution precision against objective criteria.
        </p>
      </article>

      <article style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 2rem;">
        <h2 style="font-size: 1.25rem; font-weight: 700; color: #00e5ff; margin-top: 0;">Automated Trade Journaling</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 0;">
          Eliminate manual trade logging. Every trade record logs entry deviation, corridor adherence, planned vs actual stop-loss, MAE/MFE percentiles, and execution quality.
        </p>
      </article>

      <article style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 2rem;">
        <h2 style="font-size: 1.25rem; font-weight: 700; color: #00e5ff; margin-top: 0;">Execution Controls &amp; Risk Guardrails</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 0;">
          Connect supported broker accounts with automated risk allocation, maximum daily loss stops, spread guardrails, and synchronized order lifecycle management.
        </p>
      </article>
    </section>
  </main>

  <footer style="margin-top: 4rem; padding-top: 2rem; border-top: 1px solid rgba(255,255,255,0.08); font-size: 0.85rem; color: #64748b;">
    <p style="margin-bottom: 0.75rem;">
      <strong>Financial Risk Disclosure:</strong> PrimeEdge is a specialized software platform providing quantitative analysis and decision tools for intraday traders. PrimeEdge is not an investment advisor, broker-dealer, or fund manager, and does not provide financial advice. Trading foreign exchange, indices, and commodities involves substantial risk of loss.
    </p>
    <p style="margin: 0;">
      &copy; 2026 PrimeEdge. All rights reserved. &bull; <a href="/terms" style="color: #94a3b8;">Terms of Service</a> &bull; <a href="/privacy" style="color: #94a3b8;">Privacy Policy</a> &bull; <a href="/pricing" style="color: #94a3b8;">Pricing</a>
    </p>
  </footer>
</div>
"""

PRICING_CRAWLER_HTML = """
<div class="prerender-shell" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #07090e; color: #f0f4f8; min-height: 100vh; padding: 2rem 1.5rem; max-width: 1200px; margin: 0 auto; line-height: 1.6;">
  <header style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 2rem; border-bottom: 1px solid rgba(255,255,255,0.08);">
    <a href="/" style="font-size: 1.5rem; font-weight: 700; color: #00e5ff; letter-spacing: -0.5px; text-decoration: none;">PrimeEdge</a>
    <nav style="display: flex; gap: 1.5rem; font-size: 0.95rem;">
      <a href="/" style="color: #94a3b8; text-decoration: none;">Overview</a>
      <a href="/terms" style="color: #94a3b8; text-decoration: none;">Risk Disclosure</a>
      <a href="/login" style="color: #00e5ff; text-decoration: none; font-weight: 600;">Sign In</a>
    </nav>
  </header>

  <main style="padding: 4rem 0 3rem 0;">
    <div style="text-align: center; max-width: 760px; margin: 0 auto 4rem auto;">
      <h1 style="font-size: 2.75rem; line-height: 1.2; font-weight: 800; color: #ffffff; letter-spacing: -0.03em; margin: 0 0 1.25rem 0;">
        PrimeEdge Plans &amp; Pricing
      </h1>
      <p style="font-size: 1.15rem; color: #94a3b8; margin: 0;">
        Choose the plan that fits your trading workflow. From evidence-based setup discovery to automated multi-broker execution bridges and tick-level replay.
      </p>
    </div>

    <section style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.5rem;">
      <article style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 2rem; display: flex; flex-direction: column;">
        <h2 style="font-size: 1.4rem; font-weight: 700; color: #ffffff; margin: 0 0 0.5rem 0;">Free</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 1.5rem;">Essential setup discovery and market regime intelligence.</p>
        <div style="font-size: 2.5rem; font-weight: 800; color: #ffffff; margin-bottom: 1.5rem;">$0 <span style="font-size: 1rem; color: #64748b; font-weight: normal;">/ forever</span></div>
        <ul style="list-style: none; padding: 0; margin: 0 0 2rem 0; color: #cbd5e1; font-size: 0.95rem; line-height: 2;">
          <li>&#10003; Real-time market signals (EURUSD, GBPUSD, USDJPY, XAUUSD, US100)</li>
          <li>&#10003; Decision Intelligence &amp; Market Regime Radar</li>
          <li>&#10003; Empirical P25–P75 Retracement Corridor</li>
          <li>&#10003; Historical Evidence Distributions</li>
          <li>&#10003; Basic opportunity radar &amp; scorecards</li>
          <li>&#10003; Community access</li>
        </ul>
        <a href="/register" style="margin-top: auto; display: block; text-align: center; background: rgba(255,255,255,0.06); color: #ffffff; font-weight: 600; padding: 0.85rem; border-radius: 6px; text-decoration: none; border: 1px solid rgba(255,255,255,0.12);">Start Free</a>
      </article>

      <article style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 2rem; display: flex; flex-direction: column;">
        <h2 style="font-size: 1.4rem; font-weight: 700; color: #ffffff; margin: 0 0 0.5rem 0;">Starter</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 1.5rem;">Essential market intelligence for manual traders.</p>
        <div style="font-size: 2.5rem; font-weight: 800; color: #ffffff; margin-bottom: 1.5rem;">$29 <span style="font-size: 1rem; color: #64748b; font-weight: normal;">/ month</span></div>
        <ul style="list-style: none; padding: 0; margin: 0 0 2rem 0; color: #cbd5e1; font-size: 0.95rem; line-height: 2;">
          <li>&#10003; All Free features included</li>
          <li>&#10003; Interactive Trade Planner &amp; Option A/B Analysis</li>
          <li>&#10003; Manual trade journaling &amp; execution logs</li>
          <li>&#10003; Evidence-based setup scoring &amp; risk matrix</li>
          <li>&#10003; AI Market Analyst &amp; chat assistance</li>
          <li>&#10003; Telegram commercial channel trade alerts</li>
        </ul>
        <a href="/register?plan=starter" style="margin-top: auto; display: block; text-align: center; background: rgba(255,255,255,0.06); color: #ffffff; font-weight: 600; padding: 0.85rem; border-radius: 6px; text-decoration: none; border: 1px solid rgba(255,255,255,0.12);">Get Started with Starter</a>
      </article>

      <article style="background: rgba(0,229,255,0.03); border: 2px solid #00e5ff; border-radius: 12px; padding: 2.5rem; display: flex; flex-direction: column; position: relative;">
        <div style="position: absolute; top: -14px; left: 50%; transform: translateX(-50%); background: #00e5ff; color: #07090e; font-size: 0.75rem; font-weight: 700; padding: 0.25rem 0.75rem; border-radius: 9999px; text-transform: uppercase;">Most Popular</div>
        <h2 style="font-size: 1.4rem; font-weight: 700; color: #ffffff; margin: 0 0 0.5rem 0;">Pro</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 1.5rem;">Advanced tools for serious systematic traders.</p>
        <div style="font-size: 2.5rem; font-weight: 800; color: #ffffff; margin-bottom: 1.5rem;">$99 <span style="font-size: 1rem; color: #64748b; font-weight: normal;">/ month</span></div>
        <ul style="list-style: none; padding: 0; margin: 0 0 2rem 0; color: #cbd5e1; font-size: 0.95rem; line-height: 2;">
          <li>&#10003; All Starter features included</li>
          <li>&#10003; Advanced multi-timeframe regime analysis</li>
          <li>&#10003; Historical performance &amp; MAE/MFE statistical distributions</li>
          <li>&#10003; Automated trade journaling &amp; historical replay simulator</li>
          <li>&#10003; Priority support &amp; dedicated notifications</li>
          <li>&#10003; API access (read-only)</li>
        </ul>
        <a href="/register?plan=pro" style="margin-top: auto; display: block; text-align: center; background: #00e5ff; color: #07090e; font-weight: 700; padding: 0.85rem; border-radius: 6px; text-decoration: none;">Get Started with Pro</a>
      </article>

      <article style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 2.5rem; display: flex; flex-direction: column;">
        <h2 style="font-size: 1.4rem; font-weight: 700; color: #ffffff; margin: 0 0 0.5rem 0;">Premium</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 1.5rem;">Full institutional-grade platform with auto-execution.</p>
        <div style="font-size: 2.5rem; font-weight: 800; color: #ffffff; margin-bottom: 1.5rem;">$299 <span style="font-size: 1rem; color: #64748b; font-weight: normal;">/ month</span></div>
        <ul style="list-style: none; padding: 0; margin: 0 0 2rem 0; color: #cbd5e1; font-size: 0.95rem; line-height: 2;">
          <li>&#10003; All Pro features included</li>
          <li>&#10003; Autonomous Cloud cTrader Auto-Execution</li>
          <li>&#10003; Dynamic 1% risk position sizing engine</li>
          <li>&#10003; Connected cTrader broker accounts (demo &amp; live)</li>
          <li>&#10003; Prop desk daily loss &amp; drawdown risk guardrails</li>
          <li>&#10003; Custom strategy backtesting &amp; scenario simulator</li>
          <li>&#10003; Full API access (read/write) &amp; webhook routing</li>
          <li>&#10003; Dedicated 1-on-1 priority support</li>
        </ul>
        <a href="/register?plan=premium" style="margin-top: auto; display: block; text-align: center; background: rgba(255,255,255,0.06); color: #ffffff; font-weight: 600; padding: 0.85rem; border-radius: 6px; text-decoration: none; border: 1px solid rgba(255,255,255,0.12);">Get Started with Premium</a>
      </article>
    </section>

    <section style="margin-top: 5rem; max-width: 800px; margin-left: auto; margin-right: auto;">
      <h2 style="font-size: 1.8rem; font-weight: 700; color: #ffffff; text-align: center; margin-bottom: 2rem;">Frequently Asked Questions</h2>
      <div style="border-bottom: 1px solid rgba(255,255,255,0.08); padding: 1.5rem 0;">
        <h3 style="font-size: 1.1rem; color: #00e5ff; margin: 0 0 0.5rem 0;">Is PrimeEdge a signal provider?</h3>
        <p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">No. PrimeEdge is a decision support and execution infrastructure platform. It provides statistical evaluation of setups, historical adverse distributions, and risk controls so you trade with evidence rather than arbitrary signals.</p>
      </div>
      <div style="border-bottom: 1px solid rgba(255,255,255,0.08); padding: 1.5rem 0;">
        <h3 style="font-size: 1.1rem; color: #00e5ff; margin: 0 0 0.5rem 0;">Which brokers and platforms are supported?</h3>
        <p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">PrimeEdge executes via cTrader OpenAPI with isolated execution guardrails, supporting all leading cTrader brokers including IC Markets, Pepperstone, and FP Markets.</p>
      </div>
      <div style="border-bottom: 1px solid rgba(255,255,255,0.08); padding: 1.5rem 0;">
        <h3 style="font-size: 1.1rem; color: #00e5ff; margin: 0 0 0.5rem 0;">Can I cancel or switch plans at any time?</h3>
        <p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">Yes. All paid subscriptions operate on a month-to-month basis with no long-term lock-in. You can upgrade, downgrade, or cancel whenever you choose from your account settings.</p>
      </div>
    </section>
  </main>

  <footer style="margin-top: 4rem; padding-top: 2rem; border-top: 1px solid rgba(255,255,255,0.08); font-size: 0.85rem; color: #64748b;">
    <p style="margin-bottom: 0.75rem;">
      <strong>Financial Risk Disclosure:</strong> Trading financial instruments carries substantial risk. PrimeEdge is an analytical decision platform, not a financial adviser or broker.
    </p>
    <p style="margin: 0;">
      &copy; 2026 PrimeEdge. All rights reserved. &bull; <a href="/terms" style="color: #94a3b8;">Terms of Service</a> &bull; <a href="/privacy" style="color: #94a3b8;">Privacy Policy</a>
    </p>
  </footer>
</div>
"""

NOT_FOUND_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="robots" content="noindex, follow" />
  <title>404 — Page Not Found | PrimeEdge</title>
  <style>
    body { background: #07090e; color: #f0f4f8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 1.5rem; box-sizing: border-box; }
    .box { text-align: center; max-width: 480px; }
    h1 { font-size: 4rem; color: #00e5ff; margin: 0 0 0.5rem 0; font-weight: 800; }
    p { color: #94a3b8; font-size: 1.1rem; line-height: 1.5; margin: 0 0 2rem 0; }
    a { display: inline-block; background: #00e5ff; color: #07090e; font-weight: 700; padding: 0.8rem 1.6rem; border-radius: 6px; text-decoration: none; }
  </style>
</head>
<body>
  <div class="box">
    <h1>404</h1>
    <h2>Page Not Found</h2>
    <p>The page you requested does not exist or has been moved to another address.</p>
    <a href="/">Return to PrimeEdge</a>
  </div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Metadata Configuration by Route
# ---------------------------------------------------------------------------

ROUTE_METADATA: Dict[str, Dict[str, Any]] = {
    "/": {
        "title": "PrimeEdge | Evidence-Based Trading Decisions & Risk Control",
        "description": "PrimeEdge helps intraday FX and gold traders evaluate setups with historical evidence, plan risk-aware entries and journal every decision before execution.",
        "canonical": f"{CANONICAL_DOMAIN}/",
        "robots": "index, follow",
        "og_type": "website",
        "json_ld": HOMEPAGE_JSON_LD,
        "prerender_body": HOMEPAGE_CRAWLER_HTML,
    },
    "/pricing": {
        "title": "PrimeEdge Pricing | Trading Intelligence, Replay & Execution Plans",
        "description": "Compare PrimeEdge plans for setup discovery, evidence-based trade planning, historical replay, journaling and automated execution controls.",
        "canonical": f"{CANONICAL_DOMAIN}/pricing",
        "robots": "index, follow",
        "og_type": "website",
        "json_ld": PRICING_JSON_LD,
        "prerender_body": PRICING_CRAWLER_HTML,
    },
    "/terms": {
        "title": "PrimeEdge | Terms of Service & Financial Risk Disclosure",
        "description": "PrimeEdge terms of service, acceptable use policy, and financial risk disclosures for users of quantitative trading decision software.",
        "canonical": f"{CANONICAL_DOMAIN}/terms",
        "robots": "index, follow",
        "og_type": "website",
        "json_ld": None,
        "prerender_body": None,
    },
    "/privacy": {
        "title": "PrimeEdge | Privacy Policy",
        "description": "PrimeEdge privacy policy covering data security, credential protection, and usage terms.",
        "canonical": f"{CANONICAL_DOMAIN}/privacy",
        "robots": "index, follow",
        "og_type": "website",
        "json_ld": None,
        "prerender_body": None,
    },
    "/login": {
        "title": "Sign In | PrimeEdge",
        "description": "Sign in to your PrimeEdge trading terminal and decision cockpit.",
        "canonical": f"{CANONICAL_DOMAIN}/login",
        "robots": "noindex, follow",
        "og_type": "website",
        "json_ld": None,
        "prerender_body": None,
    },
    "/register": {
        "title": "Start PrimeEdge | Evidence-Based Trading Decision Support",
        "description": "Create your PrimeEdge account and explore structured setup evidence, trade planning and historical replay tools for disciplined intraday trading.",
        "canonical": f"{CANONICAL_DOMAIN}/register",
        "robots": "noindex, follow",
        "og_type": "website",
        "json_ld": None,
        "prerender_body": None,
    },
}

# ---------------------------------------------------------------------------
# Template Assembly
# ---------------------------------------------------------------------------

def is_valid_route(path: str) -> bool:
    """Returns True if the path is an authorized SPA client route."""
    clean = ("/" + path.strip("/")).rstrip("/")
    if clean == "":
        clean = "/"
    return clean in VALID_SPA_ROUTES or any(clean.startswith(f"{prefix}/") for prefix in ["/app", "/dashboard", "/admin", "/subscription", "/replay"])


def render_html_for_route(raw_index_html: str, path: str) -> str:
    """
    Injects route-specific title, description, canonical link, Open Graph,
    Twitter Card tags, JSON-LD, and crawler-visible initial HTML into index.html.
    """
    import json
    clean = ("/" + path.strip("/")).rstrip("/")
    if clean == "":
        clean = "/"

    meta = ROUTE_METADATA.get(clean, ROUTE_METADATA["/"])
    title = meta["title"]
    description = meta["description"]
    canonical = meta.get("canonical", f"{CANONICAL_DOMAIN}{clean}")
    robots = meta.get("robots", "index, follow")
    og_type = meta.get("og_type", "website")
    image_url = f"{CANONICAL_DOMAIN}/market_os_logo_emblem.jpg"

    # Build injected head tags
    head_injections = f"""
    <title>{title}</title>
    <meta name="description" content="{description}" />
    <meta name="robots" content="{robots}" />
    <link rel="canonical" href="{canonical}" />

    <!-- Open Graph -->
    <meta property="og:type" content="{og_type}" />
    <meta property="og:site_name" content="PrimeEdge" />
    <meta property="og:url" content="{canonical}" />
    <meta property="og:title" content="{title}" />
    <meta property="og:description" content="{description}" />
    <meta property="og:image" content="{image_url}" />

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:url" content="{canonical}" />
    <meta name="twitter:title" content="{title}" />
    <meta name="twitter:description" content="{description}" />
    <meta name="twitter:image" content="{image_url}" />
"""

    if meta.get("json_ld"):
        json_str = json.dumps(meta["json_ld"], indent=2)
        head_injections += f"""
    <script type="application/ld+json">
{json_str}
    </script>
"""

    html = raw_index_html

    # Replace <title>...</title> if present
    import re
    html = re.sub(r"<title>.*?</title>", "", html, flags=re.DOTALL)
    html = re.sub(r'<meta\s+name=["\']description["\'].*?>', "", html, flags=re.DOTALL)
    html = re.sub(r'<link\s+rel=["\']canonical["\'].*?>', "", html, flags=re.DOTALL)

    # Insert new head metadata before </head>
    html = html.replace("</head>", f"{head_injections}\n  </head>")

    # Insert crawler-visible HTML inside <div id="root"></div> if available
    prerender_body = meta.get("prerender_body")
    if prerender_body:
        html = html.replace('<div id="root"></div>', f'<div id="root">{prerender_body}</div>')

    return html
