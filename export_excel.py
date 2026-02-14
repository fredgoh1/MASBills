import pandas as pd

CSV_PATH = "inventory/MAS Bills - MAS Bills.csv"
XLSX_PATH = "inventory/MAS Bills - MAS Bills.xlsx"


def main():
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df.to_excel(XLSX_PATH, index=False, engine="openpyxl")
    print(f"Exported {len(df)} rows to {XLSX_PATH}")


if __name__ == "__main__":
    main()
