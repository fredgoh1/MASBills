import argparse
import uuid
from datetime import datetime, timedelta

import pandas as pd
import requests

CSV_PATH = "inventory/MAS Bills - MAS Bills.csv"
CREDENTIALS_FILE = "Roam_Research"


def load_credentials():
    creds = {}
    with open(CREDENTIALS_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            key, _, value = line.partition("=")
            creds[key.strip()] = value.strip().strip("'\"")
    return creds["ROAM_API_TOKEN"], creds["ROAM_GRAPH_NAME"]


def _roam_session(token):
    """Create a requests session that preserves auth headers across redirects."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    # Rebuild auth on redirect so the header isn't stripped on cross-host redirects
    session.rebuild_auth = lambda prepared, response: None
    return session


def ordinal(n):
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def roam_daily_title(dt):
    """Format a date as Roam's daily page title, e.g. 'February 14th, 2026'."""
    return f"{dt.strftime('%B')} {ordinal(dt.day)}, {dt.year}"


def create_block(session, graph_name, parent_uid, text, block_uid=None):
    url = f"https://api.roamresearch.com/api/graph/{graph_name}/write"
    block = {"string": text}
    if block_uid:
        block["uid"] = block_uid
    payload = {
        "action": "create-block",
        "location": {"parent-uid": parent_uid, "order": "last"},
        "block": block,
    }
    resp = session.post(url, json=payload)
    resp.raise_for_status()


def find_or_create_page_uid(session, graph_name, title):
    """Get or create a page and return its uid."""
    url = f"https://api.roamresearch.com/api/graph/{graph_name}/q"
    query = '[:find ?uid . :where [?e :node/title "' + title + '"] [?e :block/uid ?uid]]'
    resp = session.post(url, json={"query": query})
    resp.raise_for_status()
    result = resp.json().get("result")
    if result:
        return result

    # Page doesn't exist; create it
    write_url = f"https://api.roamresearch.com/api/graph/{graph_name}/write"
    payload = {
        "action": "create-page",
        "page": {"title": title},
    }
    resp = session.post(write_url, json=payload)
    resp.raise_for_status()

    # Query again for the uid
    resp = session.post(url, json={"query": query})
    resp.raise_for_status()
    return resp.json().get("result")


def main():
    parser = argparse.ArgumentParser(
        description="Post MAS Bill auction results to Roam Research daily pages."
    )
    parser.add_argument("--date", help="Single date in yyyy-mm-dd format.")
    parser.add_argument("--from", dest="from_date", help="Start date in yyyy-mm-dd format.")
    parser.add_argument("--to", dest="to_date", help="End date in yyyy-mm-dd format.")
    args = parser.parse_args()

    if args.date:
        start = end = datetime.strptime(args.date, "%Y-%m-%d")
    elif args.from_date and args.to_date:
        start = datetime.strptime(args.from_date, "%Y-%m-%d")
        end = datetime.strptime(args.to_date, "%Y-%m-%d")
    else:
        parser.error("Provide either --date or both --from and --to.")

    token, graph_name = load_credentials()
    session = _roam_session(token)

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    auction_dates = df["Auction Date"].apply(lambda d: datetime.strptime(d, "%d/%m/%Y"))
    has_yield = df["Cut-off Yield"].fillna("").astype(str).str.strip() != ""
    date_mask = (auction_dates >= start) & (auction_dates <= end)
    target = df[date_mask & has_yield].copy()
    target["_auction_dt"] = auction_dates[target.index]

    if target.empty:
        print("No bills with Cut-off Yield found for the specified date(s).")
        return

    grouped = target.groupby("_auction_dt")

    for auction_dt, group in sorted(grouped):
        page_title = roam_daily_title(auction_dt)
        print(f"\nPosting to '{page_title}'...")

        page_uid = find_or_create_page_uid(session, graph_name, page_title)
        if not page_uid:
            print(f"  ERROR: Could not get uid for page '{page_title}'. Skipping.")
            continue

        parent_uid = str(uuid.uuid4())[:9]
        create_block(session, graph_name, page_uid, "> [!Summary]+ **MAS Bills Auction Results**", block_uid=parent_uid)

        for _, row in group.iterrows():
            text = f"> {row['Tenor']} | {row['Maturity Date']} | {row['Issue Code']} | {row['Cut-off Yield']}"
            create_block(session, graph_name, parent_uid, text)
            print(f"  {text}")

    print("\nDone.")


if __name__ == "__main__":
    main()
