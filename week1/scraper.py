from bs4 import BeautifulSoup
import requests
from playwright.async_api import async_playwright
import asyncio


# Standard headers to fetch a website
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}


def fetch_website_contents(url, use_browser=False, wait_for_selector=None, timeout=10000):
    """
    Return the title and contents of the website at the given url;
    truncate to 2,000 characters as a sensible limit
    
    Args:
        url: The URL to fetch
        use_browser: If True, use Playwright to render JavaScript (for React/SPA sites)
        wait_for_selector: Optional CSS selector to wait for before extracting content
        timeout: Timeout in milliseconds for page load (default: 10000ms)
    """
    if use_browser:
        # Check if we're in an environment with a running event loop (like Jupyter)
        try:
            loop = asyncio.get_running_loop()
            # If there's a running loop, we need to use create_task or await
            # For Jupyter compatibility, we'll use asyncio.ensure_future
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.get_event_loop().run_until_complete(_fetch_with_playwright(url, wait_for_selector, timeout))
        except RuntimeError:
            # No running loop, we can use run_until_complete safely
            return asyncio.run(_fetch_with_playwright(url, wait_for_selector, timeout))
    else:
        return _fetch_with_requests(url)


def _fetch_with_requests(url):
    """Fetch using requests - fast but doesn't execute JavaScript"""
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    title = soup.title.string if soup.title else "No title found"
    if soup.body:
        for irrelevant in soup.body(["script", "style", "img", "input"]):
            irrelevant.decompose()
        text = soup.body.get_text(separator="\n", strip=True)
    else:
        text = ""
    return (title + "\n\n" + text)[:2_000]


async def _fetch_with_playwright(url, wait_for_selector=None, timeout=10000):
    """Fetch using Playwright async API - slower but executes JavaScript (for React/SPA sites)"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Navigate to the page and wait for network to be idle
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            
            # Wait for specific selector if provided
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=timeout)
            
            # Get the rendered HTML
            content = await page.content()
            
        finally:
            await browser.close()
    
    # Parse the rendered HTML
    soup = BeautifulSoup(content, "html.parser")
    title = soup.title.string if soup.title else "No title found"
    if soup.body:
        for irrelevant in soup.body(["script", "style", "img", "input"]):
            irrelevant.decompose()
        text = soup.body.get_text(separator="\n", strip=True)
    else:
        text = ""
    return (title + "\n\n" + text)[:2_000]


def fetch_website_links(url):
    """
    Return the links on the webiste at the given url
    I realize this is inefficient as we're parsing twice! This is to keep the code in the lab simple.
    Feel free to use a class and optimize it!
    """
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    links = [link.get("href") for link in soup.find_all("a")]
    return [link for link in links if link]
