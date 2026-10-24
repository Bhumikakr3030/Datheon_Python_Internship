#!/usr/bin/env python3
"""
portfolio.py - Investment portfolio tracker.

Enter ticker symbols, buy prices and share quantities. The script computes
total invested capital, current market value, and gain/loss (absolute and %)
per holding, prints a formatted table, and appends a timestamped summary to
portfolio_summary.csv.

Price sources (in priority order):
  1. Live prices via yfinance        (only with --live; pip install yfinance)
  2. Built-in SAMPLE_PRICES table    (illustrative values, NOT real quotes)
  3. Manual entry                    (asked interactively if a price is missing)

Optional: pass --constituents constituents.csv (the S&P 500 dataset from
https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv)
to validate tickers and show company name / sector. That file has no prices;
it is used for reference data only.

Usage:
  python portfolio.py                       # interactive entry
  python portfolio.py --demo                # run with a built-in sample portfolio
  python portfolio.py --live                # fetch live prices with yfinance
  python portfolio.py --constituents constituents.csv
"""

import argparse
import csv
import os
import sys
from datetime import datetime

OUTPUT_FILE = "portfolio_summary.csv"

# Illustrative prices for offline use. Replace or use --live for real data.
SAMPLE_PRICES = {
    "AAPL": 228.50, "MSFT": 425.30, "GOOGL": 172.80, "AMZN": 186.40,
    "NVDA": 135.20, "TSLA": 245.60, "JPM": 215.10, "JNJ": 158.90,
    "KO": 70.25, "XOM": 118.40,
}

# Positions: {ticker: {"buy_price": float, "shares": float}}
DEMO_POSITIONS = {
    "AAPL": {"buy_price": 190.00, "shares": 25},
    "MSFT": {"buy_price": 380.50, "shares": 10},
    "NVDA": {"buy_price": 95.00, "shares": 40},
    "KO":   {"buy_price": 72.10, "shares": 50},
    "XOM":  {"buy_price": 110.00, "shares": 30},
}

CSV_FIELDS = [
    "run_timestamp", "ticker", "company", "sector", "shares", "buy_price",
    "current_price", "invested", "market_value", "gain_loss", "gain_loss_pct",
]


# ---------- Reference data ----------

def load_constituents(path):
    """Return {symbol: (company, sector)} from the S&P 500 constituents CSV."""
    info = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                info[row["Symbol"].strip().upper()] = (
                    row.get("Security", "").strip(),
                    row.get("GICS Sector", "").strip(),
                )
    except OSError as e:
        print(f"Warning: could not read {path}: {e}")
    return info


# ---------- Price lookup ----------

def fetch_live_price(ticker):
    """Latest close via yfinance, or None on any failure."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker.replace(".", "-")).history(period="5d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def get_price(ticker, live, interactive):
    if live:
        price = fetch_live_price(ticker)
        if price is not None:
            return price, "live"
        print(f"  Live price unavailable for {ticker}; falling back.")
    if ticker in SAMPLE_PRICES:
        return SAMPLE_PRICES[ticker], "sample"
    if interactive:
        while True:
            raw = input(f"  No price known for {ticker}. Enter current price: ").strip()
            try:
                value = float(raw)
                if value > 0:
                    return value, "manual"
            except ValueError:
                pass
            print("  Please enter a positive number.")
    return None, "missing"


# ---------- Input ----------

def prompt_positive(label):
    while True:
        raw = input(label).strip().replace(",", "")
        try:
            value = float(raw)
            if value > 0:
                return value
        except ValueError:
            pass
        print("  Please enter a positive number.")


def collect_positions(constituents):
    positions = {}
    print("Enter your holdings. Leave the ticker blank to finish.\n")
    while True:
        ticker = input("Ticker symbol: ").strip().upper()
        if not ticker:
            if positions:
                break
            print("  Add at least one holding.")
            continue
        if constituents and ticker not in constituents:
            print(f"  Note: {ticker} is not in the S&P 500 list (continuing anyway).")
        buy_price = prompt_positive("  Buy price per share: ")
        shares = prompt_positive("  Number of shares: ")
        if ticker in positions:
            # Merge into a weighted-average cost basis.
            old = positions[ticker]
            total_shares = old["shares"] + shares
            avg = (old["buy_price"] * old["shares"] + buy_price * shares) / total_shares
            positions[ticker] = {"buy_price": avg, "shares": total_shares}
            print(f"  Merged with existing {ticker} position (avg cost {avg:.2f}).")
        else:
            positions[ticker] = {"buy_price": buy_price, "shares": shares}
    return positions


# ---------- Calculations ----------

def analyze(positions, constituents, live, interactive):
    rows = []
    for ticker, pos in positions.items():
        price, source = get_price(ticker, live, interactive)
        if price is None:
            print(f"Skipping {ticker}: no price available.")
            continue
        invested = pos["buy_price"] * pos["shares"]
        value = price * pos["shares"]
        gain = value - invested
        pct = (gain / invested * 100) if invested else 0.0
        company, sector = constituents.get(ticker, ("", ""))
        rows.append({
            "ticker": ticker, "company": company, "sector": sector,
            "shares": pos["shares"], "buy_price": pos["buy_price"],
            "current_price": price, "invested": invested,
            "market_value": value, "gain_loss": gain, "gain_loss_pct": pct,
            "source": source,
        })
    return rows


def totals(rows):
    invested = sum(r["invested"] for r in rows)
    value = sum(r["market_value"] for r in rows)
    gain = value - invested
    pct = (gain / invested * 100) if invested else 0.0
    return invested, value, gain, pct


# ---------- Output ----------

def print_report(rows):
    header = (f"{'Ticker':<8}{'Shares':>9}{'Buy':>11}{'Current':>11}"
              f"{'Invested':>14}{'Value':>14}{'Gain/Loss':>13}{'%':>9}")
    line = "-" * len(header)
    print("\n" + "PORTFOLIO SUMMARY".center(len(header)))
    print(f"{datetime.now():%Y-%m-%d %H:%M}".center(len(header)))
    print(line)
    print(header)
    print(line)
    for r in rows:
        print(f"{r['ticker']:<8}{r['shares']:>9,.2f}{r['buy_price']:>11,.2f}"
              f"{r['current_price']:>11,.2f}{r['invested']:>14,.2f}"
              f"{r['market_value']:>14,.2f}{r['gain_loss']:>+13,.2f}"
              f"{r['gain_loss_pct']:>+8.2f}%")
    print(line)
    invested, value, gain, pct = totals(rows)
    print(f"{'TOTAL':<8}{'':>9}{'':>11}{'':>11}{invested:>14,.2f}"
          f"{value:>14,.2f}{gain:>+13,.2f}{pct:>+8.2f}%")
    print(line)
    sources = sorted({r["source"] for r in rows})
    if "sample" in sources:
        print("Note: 'sample' prices are illustrative, not live quotes. Use --live for real data.")


def log_to_csv(rows, path):
    """Append this run's summary (one row per holding plus a TOTAL row)."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_file = not os.path.exists(path) or os.path.getsize(path) == 0
    invested, value, gain, pct = totals(rows)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if new_file:
            writer.writeheader()
        for r in rows:
            writer.writerow({
                "run_timestamp": stamp, "ticker": r["ticker"],
                "company": r["company"], "sector": r["sector"],
                "shares": f"{r['shares']:.4f}".rstrip("0").rstrip("."),
                "buy_price": f"{r['buy_price']:.2f}",
                "current_price": f"{r['current_price']:.2f}",
                "invested": f"{r['invested']:.2f}",
                "market_value": f"{r['market_value']:.2f}",
                "gain_loss": f"{r['gain_loss']:.2f}",
                "gain_loss_pct": f"{r['gain_loss_pct']:.2f}",
            })
        writer.writerow({
            "run_timestamp": stamp, "ticker": "TOTAL", "company": "", "sector": "",
            "shares": "", "buy_price": "", "current_price": "",
            "invested": f"{invested:.2f}", "market_value": f"{value:.2f}",
            "gain_loss": f"{gain:.2f}", "gain_loss_pct": f"{pct:.2f}",
        })
    print(f"\nSummary appended to {path}")


# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser(description="Investment portfolio tracker")
    parser.add_argument("--demo", action="store_true", help="use a built-in sample portfolio")
    parser.add_argument("--live", action="store_true", help="fetch live prices via yfinance")
    parser.add_argument("--constituents", help="path to S&P 500 constituents.csv")
    parser.add_argument("--output", default=OUTPUT_FILE, help=f"CSV log file (default {OUTPUT_FILE})")
    args = parser.parse_args()

    constituents = load_constituents(args.constituents) if args.constituents else {}

    if args.demo:
        positions = DEMO_POSITIONS
        interactive = False
    else:
        positions = collect_positions(constituents)
        interactive = True

    rows = analyze(positions, constituents, args.live, interactive)
    if not rows:
        print("No holdings could be priced. Nothing to report.")
        sys.exit(1)

    print_report(rows)
    log_to_csv(rows, args.output)


if __name__ == "__main__":
    main()
