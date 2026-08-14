from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

try:
    import FinanceDataReader as fdr
except ImportError as exc:
    raise SystemExit(
        "FinanceDataReader is not installed. Run: python -m pip install -r requirements.txt"
    ) from exc


DEFAULT_SYMBOLS = {
    "KS11": "KOSPI",
    "KQ11": "KOSDAQ",
    "DJI": "Dow Jones",
    "IXIC": "NASDAQ Composite",
    "US500": "S&P 500",
    "USD/KRW": "USD/KRW",
}


@dataclass
class SymbolResult:
    symbol: str
    label: str
    rows: int = 0
    latest_date: str = "-"
    latest_close: str = "-"
    change_value: str = "-"
    change_percent: str = "-"
    change_direction: str = "flat"
    table_html: str = ""
    error: str | None = None


@dataclass
class MarketListingResult:
    market: str
    label: str
    rows: int = 0
    total_marcap: str = "-"
    table_html: str = ""
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a daily FinanceDataReader briefing as HTML."
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory where HTML reports are written.",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=45,
        help="Number of calendar days to request for each symbol.",
    )
    parser.add_argument(
        "--table-rows",
        type=int,
        default=8,
        help="Number of recent rows to include per symbol table.",
    )
    parser.add_argument(
        "--date",
        dest="run_date",
        default=date.today().isoformat(),
        help="Report date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help='Symbol to include. Use "SYMBOL=Label" for a custom label.',
    )
    parser.add_argument(
        "--kospi-listing-rows",
        type=int,
        default=20,
        help="Number of KOSPI listed stocks to include by market cap.",
    )
    parser.add_argument(
        "--no-kospi-listing",
        action="store_true",
        help="Skip the KOSPI listed stocks section.",
    )
    return parser.parse_args()


def parse_symbol(value: str) -> tuple[str, str]:
    if "=" in value:
        symbol, label = value.split("=", 1)
        symbol = symbol.strip()
        label = label.strip() or symbol
        return symbol, label

    symbol = value.strip()
    return symbol, symbol


def format_number(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"

    if math.isnan(number):
        return "-"
    if abs(number) >= 1000:
        return f"{number:,.2f}"
    if abs(number) >= 1:
        return f"{number:,.4f}".rstrip("0").rstrip(".")
    return f"{number:.6f}".rstrip("0").rstrip(".")


def format_date(value: object) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def format_percent(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if math.isnan(number):
        return "-"
    return f"{number:.2f}%"


def table_html(frame, table_rows: int) -> str:
    columns = [
        column
        for column in ["Open", "High", "Low", "Close", "Volume", "Change"]
        if column in frame.columns
    ]
    recent = frame.tail(table_rows).copy()
    if columns:
        recent = recent[columns]
    recent.index = [format_date(index_value) for index_value in recent.index]
    recent.index.name = "Date"
    return recent.to_html(classes="data-table", border=0, escape=True)


def listing_table_html(frame, listing_rows: int) -> str:
    display_columns = [
        column
        for column in [
            "Code",
            "Name",
            "Close",
            "Changes",
            "ChagesRatio",
            "Volume",
            "Amount",
            "Marcap",
        ]
        if column in frame.columns
    ]
    listing = frame.copy()
    if "Marcap" in listing.columns:
        listing = listing.sort_values("Marcap", ascending=False)
    listing = listing.head(listing_rows)
    listing = listing[display_columns]
    listing = listing.rename(
        columns={
            "ChagesRatio": "ChangeRatio",
            "Marcap": "MarketCap",
        }
    )

    for column in ["Close", "Changes", "Volume", "Amount", "MarketCap"]:
        if column in listing.columns:
            listing[column] = listing[column].map(format_number)
    if "ChangeRatio" in listing.columns:
        listing["ChangeRatio"] = listing["ChangeRatio"].map(format_percent)

    return listing.to_html(classes="data-table", border=0, index=False, escape=True)


def fetch_kospi_listing(listing_rows: int) -> MarketListingResult:
    result = MarketListingResult(market="KOSPI", label="KOSPI Listed Stocks")

    try:
        frame = fdr.StockListing("KOSPI")
    except Exception as exc:
        result.error = str(exc)
        return result

    if frame is None or frame.empty:
        result.error = "No KOSPI listing rows returned."
        return result

    result.rows = len(frame)
    if "Marcap" in frame.columns:
        result.total_marcap = format_number(frame["Marcap"].sum())
    result.table_html = listing_table_html(frame, listing_rows)
    return result


def fetch_symbol(
    symbol: str,
    label: str,
    start_date: str,
    table_rows: int,
) -> SymbolResult:
    result = SymbolResult(symbol=symbol, label=label)

    try:
        frame = fdr.DataReader(symbol, start_date)
    except Exception as exc:
        result.error = str(exc)
        return result

    if frame is None or frame.empty:
        result.error = "No rows returned."
        return result

    result.rows = len(frame)
    close = frame["Close"].dropna() if "Close" in frame.columns else None

    if close is not None and not close.empty:
        latest = close.iloc[-1]
        result.latest_close = format_number(latest)
        result.latest_date = format_date(close.index[-1])

        if len(close) >= 2:
            previous = close.iloc[-2]
            change = float(latest) - float(previous)
            result.change_value = format_number(change)
            if float(previous) != 0:
                result.change_percent = f"{(change / float(previous)) * 100:.2f}%"
            if change > 0:
                result.change_direction = "up"
            elif change < 0:
                result.change_direction = "down"
    else:
        result.latest_date = format_date(frame.index[-1])

    result.table_html = table_html(frame, table_rows)
    return result


def build_html(
    results: list[SymbolResult],
    market_listing: MarketListingResult | None,
    generated_at: datetime,
    report_date: date,
    start_date: date,
) -> str:
    card_items = [build_card(result) for result in results]
    if market_listing is not None:
        card_items.append(build_market_card(market_listing))
    cards = "\n".join(card_items)

    section_items = [build_section(result) for result in results]
    if market_listing is not None:
        section_items.append(build_market_section(market_listing))
    sections = "\n".join(section_items)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Daily Finance Briefing - {escape(report_date.isoformat())}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fb;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #667085;
      --line: #d9dee8;
      --up: #047857;
      --down: #b42318;
      --accent: #1d4ed8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.5;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 20px 48px;
    }}
    header {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 20px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 18px;
      margin-bottom: 22px;
    }}
    h1 {{
      margin: 0 0 4px;
      font-size: 28px;
      line-height: 1.2;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    p {{ margin: 0; }}
    .meta {{
      color: var(--muted);
      font-size: 13px;
      text-align: right;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .label {{
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 8px;
    }}
    .value {{
      font-size: 22px;
      font-weight: 700;
      line-height: 1.2;
      word-break: break-word;
    }}
    .subvalue {{
      color: var(--muted);
      font-size: 12px;
      margin-top: 6px;
    }}
    .up {{ color: var(--up); }}
    .down {{ color: var(--down); }}
    .flat {{ color: var(--muted); }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin-top: 14px;
      padding: 16px;
      overflow-x: auto;
    }}
    .section-meta {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 12px;
    }}
    .error {{
      border-left: 4px solid var(--down);
      padding: 10px 12px;
      background: #fff4f2;
      color: var(--down);
    }}
    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      white-space: nowrap;
    }}
    .data-table th,
    .data-table td {{
      border-bottom: 1px solid var(--line);
      padding: 8px 10px;
      text-align: right;
    }}
    .data-table th:first-child,
    .data-table td:first-child {{
      text-align: left;
    }}
    .data-table thead th {{
      color: var(--muted);
      font-weight: 700;
      background: #f2f5fa;
    }}
    @media (max-width: 700px) {{
      header {{
        display: block;
      }}
      .meta {{
        text-align: left;
        margin-top: 10px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Daily Finance Briefing</h1>
        <p class="subvalue">Report date: {escape(report_date.isoformat())}</p>
      </div>
      <div class="meta">
        <p>Generated: {escape(generated_at.strftime("%Y-%m-%d %H:%M:%S"))}</p>
        <p>Data start: {escape(start_date.isoformat())}</p>
      </div>
    </header>
    <div class="cards">
      {cards}
    </div>
    {sections}
  </main>
</body>
</html>
"""


def build_card(result: SymbolResult) -> str:
    label = escape(result.label)
    symbol = escape(result.symbol)
    direction = escape(result.change_direction)

    if result.error:
        value = "Error"
        subvalue = escape(result.error)
        direction = "down"
    else:
        value = escape(result.latest_close)
        subvalue = escape(
            f"{result.latest_date} | {result.change_value} ({result.change_percent})"
        )

    return f"""<article class="card">
  <p class="label">{label} ({symbol})</p>
  <p class="value {direction}">{value}</p>
  <p class="subvalue">{subvalue}</p>
</article>"""


def build_section(result: SymbolResult) -> str:
    title = f"{result.label} ({result.symbol})"
    if result.error:
        body = f'<div class="error">{escape(result.error)}</div>'
    else:
        body = result.table_html

    return f"""<section>
  <h2>{escape(title)}</h2>
  <p class="section-meta">Rows: {result.rows} | Latest: {escape(result.latest_date)}</p>
  {body}
</section>"""


def build_market_card(result: MarketListingResult) -> str:
    label = escape(result.label)
    market = escape(result.market)

    if result.error:
        value = "Error"
        subvalue = escape(result.error)
        direction = "down"
    else:
        value = f"{result.rows:,}"
        subvalue = escape(f"Total market cap: {result.total_marcap}")
        direction = "flat"

    return f"""<article class="card">
  <p class="label">{label} ({market})</p>
  <p class="value {direction}">{value}</p>
  <p class="subvalue">{subvalue}</p>
</article>"""


def build_market_section(result: MarketListingResult) -> str:
    if result.error:
        body = f'<div class="error">{escape(result.error)}</div>'
    else:
        body = result.table_html

    return f"""<section>
  <h2>{escape(result.label)}</h2>
  <p class="section-meta">Rows: {result.rows} | Total market cap: {escape(result.total_marcap)}</p>
  {body}
</section>"""


def write_report(html_text: str, output_dir: Path, report_date: date) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dated_path = output_dir / f"daily-finance-{report_date.isoformat()}.html"
    latest_path = output_dir / "latest.html"
    dated_path.write_text(html_text, encoding="utf-8")
    latest_path.write_text(html_text, encoding="utf-8")
    return dated_path, latest_path


def main() -> int:
    args = parse_args()
    report_date = date.fromisoformat(args.run_date)
    start_date = report_date - timedelta(days=args.lookback_days)

    symbol_items = (
        [parse_symbol(value) for value in args.symbol]
        if args.symbol
        else list(DEFAULT_SYMBOLS.items())
    )

    results = [
        fetch_symbol(symbol, label, start_date.isoformat(), args.table_rows)
        for symbol, label in symbol_items
    ]
    market_listing = (
        None
        if args.no_kospi_listing
        else fetch_kospi_listing(args.kospi_listing_rows)
    )
    html_text = build_html(
        results,
        market_listing,
        datetime.now(),
        report_date,
        start_date,
    )
    dated_path, latest_path = write_report(html_text, Path(args.output_dir), report_date)

    print(f"Wrote {dated_path}")
    print(f"Wrote {latest_path}")
    return 0 if any(result.error is None for result in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
