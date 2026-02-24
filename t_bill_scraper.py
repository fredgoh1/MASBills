import time

import pandas as pd

from scraper import create_driver, convert_date, scrape_cutoff_yield

CSV_PATH = "inventory/SGS Treasury Bills - T-BILLS.csv"

AUCTION_URL = (
    "https://www.mas.gov.sg/bonds-and-bills/auctions-and-issuance-calendar/"
    "auction-t-bill?issue_code={issue_code}&issue_date={issue_date}"
)


def main():
    df = pd.read_csv(CSV_PATH, encoding="utf-8")

    if "Cut-off Yield" not in df.columns:
        df["Cut-off Yield"] = ""

    closed_mask = df["Status"] == "Closed"
    closed_count = closed_mask.sum()
    print(f"Found {closed_count} closed T-Bills to scrape.\n")

    driver = create_driver()
    try:
        for idx in df[closed_mask].index:
            issue_code = df.at[idx, "Issue Code"]
            issue_date = df.at[idx, "Issue Date"]
            tenor = df.at[idx, "Tenor"]

            print(f"Scraping {issue_code} ({tenor})...", end=" ", flush=True)

            yield_value = scrape_cutoff_yield(driver, issue_code, issue_date, url_template=AUCTION_URL)
            if yield_value:
                df.at[idx, "Cut-off Yield"] = yield_value
                print(f"{yield_value}")
            else:
                print("NOT FOUND")

            time.sleep(1.5)
    finally:
        driver.quit()

    df.to_csv(CSV_PATH, index=False, encoding="utf-8")
    print(f"\nDone. CSV updated at {CSV_PATH}")


if __name__ == "__main__":
    main()
