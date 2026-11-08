import sys
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.itesca_activity_portal import BASE_URL, _browser_resolver_args, _get_credentials

load_dotenv(ROOT / "aulaTEX/aulatex.env")
creds = _get_credentials(ROOT)
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=_browser_resolver_args()[0])
    page = b.new_page()
    page.goto(f"{BASE_URL}/login/index.php")
    page.locator("#username").fill(creds["username"])
    page.locator("#password").fill(creds["password"])
    page.locator("#loginbtn").click()
    page.wait_for_load_state("networkidle")
    page.goto(f"{BASE_URL}/mod/quiz/view.php?id=1756")
    page.wait_for_load_state("networkidle")
    print("VIEW URL:", page.url)
    print("VIEW TEXT:\n", page.locator("#region-main").inner_text())
    page.screenshot(path="ITESCA/check_view.png", full_page=True)

    page.goto(f"{BASE_URL}/mod/quiz/attempt.php?attempt=6841&cmid=1756")
    page.wait_for_load_state("networkidle")
    print("ATTEMPT URL:", page.url)
    print("ATTEMPT TEXT:\n", page.locator("#region-main").inner_text())
    page.screenshot(path="ITESCA/check_attempt.png", full_page=True)
    b.close()

