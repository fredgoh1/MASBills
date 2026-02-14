import argparse
import time

import pandas as pd
from datetime import datetime

from scraper import CSV_PATH, create_driver, convert_date, scrape_cutoff_yield


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Cut-off Yield for upcoming MAS Bills up to a given date."
    )
    parser.add_argument(
        "date",
        help="Cutoff date in yyyy-mm-dd format. Bills with Auction Date on or before this date will be scraped.",
    )
    args = parser.parse_args()

    cutoff_date = datetime.strptime(args.date, "%Y-%m-%d")

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    if "Cut-off Yield" not in df.columns:
        df["Cut-off Yield"] = ""

    upcoming_mask = df["Status"] == "Upcoming"
    auction_dates = df["Auction Date"].apply(
        lambda d: datetime.strptime(d, "%d/%m/%Y")
    )
    date_mask = auction_dates <= cutoff_date

    target_mask = upcoming_mask & date_mask
    target_count = target_mask.sum()

    if target_count == 0:
        print(f"No upcoming bills with Auction Date on or before {args.date}.")
        return

    print(f"Found {target_count} upcoming bill(s) to scrape.\n")

    driver = create_driver()
    try:
        for idx in df[target_mask].index:
            issue_code = df.at[idx, "Issue Code"]
            issue_date = df.at[idx, "Issue Date"]
            tenor = df.at[idx, "Tenor"]

            print(f"Scraping {issue_code} ({tenor})...", end=" ", flush=True)

            yield_value = scrape_cutoff_yield(driver, issue_code, issue_date)
            if yield_value:
                df.at[idx, "Cut-off Yield"] = yield_value
                df.at[idx, "Status"] = "Closed"
                print(f"{yield_value}")
            else:
                print("NOT FOUND")

            time.sleep(1.5)
    finally:
        driver.quit()

    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"\nDone. CSV updated at {CSV_PATH}")


if __name__ == "__main__":
    main()
