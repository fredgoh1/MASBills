import sys
import argparse
import datetime
import scrape_upcoming
import post_to_roam

def main():
    parser = argparse.ArgumentParser(description="Scrape upcoming MAS Bills and post to Roam")
    parser.add_argument("--date", default=str(datetime.date.today()), help="Cutoff auction date (YYYY-MM-DD), defaults to today")
    args = parser.parse_args()

    print(f"[1/2] Scraping upcoming MAS Bills up to {args.date}...")
    sys.argv = ["scrape_upcoming.py", args.date]
    scraped = scrape_upcoming.main()

    if not scraped:
        print("No bills were scraped — skipping Roam post.")
        return

    print(f"[2/2] Posting MAS Bills results to Roam for {args.date}...")
    sys.argv = ["post_to_roam.py", "--date", args.date]
    post_to_roam.main()

if __name__ == "__main__":
    main()
