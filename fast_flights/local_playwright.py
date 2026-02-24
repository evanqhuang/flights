from typing import Any, Optional
import asyncio
from playwright.async_api import async_playwright, ProxySettings

_BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}
_BLOCKED_DOMAINS = [
    "googlesyndication.com",
    "doubleclick.net",
    "googletagmanager.com",
    "google-analytics.com",
]


async def _handle_route(route):
    """Block unnecessary resources to save bandwidth."""
    if route.request.resource_type in _BLOCKED_RESOURCE_TYPES:
        await route.abort()
    elif any(domain in route.request.url for domain in _BLOCKED_DOMAINS):
        await route.abort()
    else:
        await route.continue_()


async def fetch_with_playwright(url: str, playwright_url: Optional[str] = None, proxy: Optional[ProxySettings] = None) -> str:
    """
    Fetch content from a URL using Playwright browser automation.

    Args:
        url: Target URL to fetch
        playwright_url: WebSocket endpoint (ws:// or wss://) for remote Playwright instance.
                       If None, launches local Chromium browser.
        proxy: Optional proxy configuration dict with 'server', 'username', 'password' keys.

    Returns:
        HTML content from the page's main role element
    """
    async with async_playwright() as p:
        context = None
        if playwright_url:
            # Connect to remote Playwright instance (e.g., Docker container)
            browser = await p.chromium.connect(playwright_url)
            if proxy:
                # For remote browsers, apply proxy at context level
                context = await browser.new_context(proxy=proxy)
                page = await context.new_page()
            else:
                page = await browser.new_page()
        else:
            # Launch local Chromium instance with proxy at launch level
            browser = await p.chromium.launch(proxy=proxy)
            page = await browser.new_page()

        await page.route("**/*", _handle_route)
        await page.goto(url)
        if page.url.startswith("https://consent.google.com"):
            await page.click('text="Accept all"')
        locator = page.locator('.eQ35Ce')
        await locator.wait_for()
        body = await page.evaluate(
            "() => document.querySelector('[role=\"main\"]').innerHTML"
        )

        # Cleanup
        if context:
            await context.close()
        if not playwright_url:
            # Only close browser if we launched it locally
            # Remote browsers should be managed by their container
            await browser.close()
    return body

async def fetch_with_playwright_page(page, url: str) -> str:
    """Fetch Google Flights HTML using an already-acquired Playwright page.

    This is the context-pool-aware entry point. The caller is responsible
    for page lifecycle (acquiring from pool, releasing after use).
    Resource blocking should be configured at the context level by the pool.
    """
    await page.goto(url)
    if page.url.startswith("https://consent.google.com"):
        await page.click('text="Accept all"')
    locator = page.locator('.eQ35Ce')
    await locator.wait_for(timeout=30000)
    body = await page.evaluate(
        "() => document.querySelector('[role=\"main\"]').innerHTML"
    )
    return body


def local_playwright_fetch(params: dict, playwright_url: Optional[str] = None, proxy: Optional[ProxySettings] = None) -> Any:
    """
    Fetch Google Flights data using Playwright.

    Args:
        params: Query parameters for the Google Flights URL
        playwright_url: WebSocket endpoint (ws:// or wss://) for remote Playwright instance.
                       If None, uses local Chromium browser.
        proxy: Optional proxy configuration dict with 'server', 'username', 'password' keys.

    Returns:
        DummyResponse object with fetched content
    """
    url = "https://www.google.com/travel/flights?" + "&".join(f"{k}={v}" for k, v in params.items())
    body = asyncio.run(fetch_with_playwright(url, playwright_url, proxy))

    class DummyResponse:
        status_code = 200
        text = body
        text_markdown = body

    return DummyResponse
