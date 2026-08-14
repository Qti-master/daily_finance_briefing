# Daily Finance Briefing

This workspace contains a small FinanceDataReader job that writes a daily HTML
report.

## GitHub Actions Schedule

The workflow at `.github/workflows/daily-finance-briefing.yml` runs every day at
10:00 AM in the `Asia/Seoul` timezone.

It writes the HTML files to `reports/` and commits them back to the repository:

- `reports/daily-finance-YYYY-MM-DD.html`
- `reports/latest.html`

You can also run it manually from the repository's **Actions** tab by selecting
`Daily Finance Briefing` and choosing **Run workflow**.

If the workflow fails, it creates a GitHub Issue titled
`Codex: Daily Finance Briefing failed on YYYY-MM-DD`. The issue includes the run
URL and captured error logs, and is labeled `codex`, `github-actions`, and
`failure` so it can be handed to Codex for repair.

## Requirements

- Python 3.9 or newer
- Dependencies from `requirements.txt`

Install dependencies after creating or activating your Python environment:

```powershell
python -m pip install -r requirements.txt
```

This workspace also includes `uv`, so the local `.venv` can be refreshed with:

```powershell
.\tools\uv\uv.exe pip install -r requirements.txt --python .\.venv\Scripts\python.exe --cache-dir .\.uv-cache
```

## Run Once

```powershell
.\scripts\run_daily_briefing.ps1
```

The script writes:

- `reports\daily-finance-YYYY-MM-DD.html`
- `reports\latest.html`

By default, the report includes the KOSPI index (`KS11`) and a KOSPI listed
stocks section with the top 20 companies by market capitalization.

## Customize Symbols

Pass one or more `--symbol` values. Use `SYMBOL=Label` when you want a readable
label in the report.

```powershell
.\scripts\run_daily_briefing.ps1 --symbol "005930=Samsung Electronics" --symbol "000660=SK Hynix"
```

Adjust the number of KOSPI listed stocks:

```powershell
.\scripts\run_daily_briefing.ps1 --kospi-listing-rows 50
```

Skip the KOSPI listed stocks section:

```powershell
.\scripts\run_daily_briefing.ps1 --no-kospi-listing
```
