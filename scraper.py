import re
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

CSV_PATH = "inventory/MAS Bills - MAS Bills.csv"

AUCTION_URL = (
    "https://www.mas.gov.sg/bonds-and-bills/auctions-and-issuance-calendar/"
    "auction-mas-bill?issue_code={issue_code}&issue_date={issue_date}"
)


def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'},
    )
    return driver


def convert_date(date_str):
    """Convert DD/MM/YYYY to YYYY-MM-DD."""
    return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")


def scrape_cutoff_yield(driver, issue_code, issue_date_ddmmyyyy):
    """Scrape Cut-off Yield for a single bill from the MAS auction page."""
    issue_date = convert_date(issue_date_ddmmyyyy)
    url = AUCTION_URL.format(issue_code=issue_code, issue_date=issue_date)
    driver.get(url)

    try:
        time.sleep(5)  # Wait for dynamic content to render

        source = driver.page_source

        # Primary strategy: parse dt/dd pairs from page source.
        # The auction results section uses <dt>Cut-off Yield</dt><dd>VALUE</dd>
        # but is often in a collapsed/hidden section not visible via .text.
        match = re.search(
            r"<dt>\s*Cut-off Yield\s*</dt>\s*<dd>\s*(.*?)\s*</dd>",
            source,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            value = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            if value:
                return value

        # Fallback: check visible body text
        body_text = driver.find_element(By.TAG_NAME, "body").text
        lines = body_text.split("\n")
        for i, line in enumerate(lines):
            if "cut-off yield" in line.lower():
                parts = line.split()
                for part in parts:
                    part_clean = part.replace("%", "").replace(",", "")
                    try:
                        float(part_clean)
                        return part
                    except ValueError:
                        continue
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line:
                        return next_line

        print(f"  WARNING: Could not find Cut-off Yield on page for {issue_code}")
        print(f"  URL: {url}")
        return None

    except Exception as e:
        print(f"  ERROR scraping {issue_code}: {e}")
        return None


def main():
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    closed_mask = df["Status"] == "Closed"
    closed_count = closed_mask.sum()
    print(f"Found {closed_count} closed bills to scrape.\n")

    if "Cut-off Yield" not in df.columns:
        df["Cut-off Yield"] = ""

    driver = create_driver()
    try:
        for idx in df[closed_mask].index:
            issue_code = df.at[idx, "Issue Code"]
            issue_date = df.at[idx, "Issue Date"]
            tenor = df.at[idx, "Tenor"]

            print(f"Scraping {issue_code} ({tenor})...", end=" ", flush=True)

            yield_value = scrape_cutoff_yield(driver, issue_code, issue_date)
            if yield_value:
                df.at[idx, "Cut-off Yield"] = yield_value
                print(f"{yield_value}")
            else:
                print("NOT FOUND")

            time.sleep(1.5)  # Rate limiting
    finally:
        driver.quit()

    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"\nDone. CSV updated at {CSV_PATH}")


if __name__ == "__main__":
    main()
