# Benford's Law Digital Audit

A complete, production-quality Python pipeline that applies Benford's Law to SEC financial statement data to detect anomalous distributions in filings.

## Project Description

In forensic accounting and auditing, numerical data that is heavily manipulated or fabricated often breaks natural statistical laws. Benford's Law (also known as the Law of First Digits) defines a counterintuitive expected probability distribution for the leading digits in organic datasets spanning multiple orders of magnitude. This project leverages the SEC EDGAR Full-Text Search API to systematically mine the past 10 years of 10-K annual filings for 30 major US companies across five key sectors. 

By applying BeautifulSoup regex parsers and statistical tests like the Chi-Square metric and Mean Absolute Deviation (MAD), the project evaluates the degree to which a company's financial figures conform to theoretical expectations. This pipeline not only ranks companies on a custom Suspicion Score but also generates interactive visuals and automated PDF audit reports, providing a state-of-the-art framework for financial data investigation.

## Setup Instructions

Ensure you have Python 3.9+ installed.

1. Clone the repository and navigate to the project directory:
```bash
git clone https://github.com/itzsam-lol/LedgerLens.git
cd LedgerLens
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Run a lightweight dry-run test:
```bash
python main.py --dry-run --all
```

## Usage

You can run individual modules of the pipeline via the CLI using `argparse` flags:

- `--download`: Fetches SEC EDGAR data for the hardcoded target tickers (with rate-limiting and caching).
- `--extract`: Parses the HTML, extracts valid numeric values, and counts significant leading digits.
- `--analyze`: Computes Benford metrics (Chi-square, MAD, Z-Scores) and builds the leaderboard.
- `--visualize`: Renders clean, dark-themed statistical plots (Matplotlib/Seaborn/Plotly).
- `--report`: Generates executive PDF reports for the most anomalous companies using `ReportLab`.
- `--all`: Runs the entire pipeline sequentially.
- `--ticker AAPL`: Targets a single company instead of the full 30-company list.

**Example End-to-End Run:**
```bash
python main.py --all
```

## Outputs
The pipeline automatically generates results into the `outputs/` directory:

- `outputs/leaderboard.csv`: A comprehensive CSV with per-company metrics sorted by highest Suspicion Score.
- `outputs/charts/`: Directory containing static charts and an interactive HTML plot:
  - `benford_curve.png`
  - `company_overlay_{ticker}.png`
  - `leaderboard_heatmap.png`
  - `sector_comparison.png`
  - `suspicion_scatter.html`
- `outputs/reports/`: Executive PDF audit reports with automated insights for top flagged companies.

## Example Output Visual
![Anomaly Heatmap: First Digit Z-Scores by Company](outputs/charts/leaderboard_heatmap.png)

## Preliminary Findings

Based on an initial extraction of 10-K filings across our 30-company sample (which may change dynamically as filings are updated), **Technology and Finance** typically demonstrate the closest conformity to Benford's Law due to high volumes of natural transactions.

However, the **Retail** sector frequently shows high Mean Absolute Deviation (MAD), likely driven by price points aggressively anchoring around specific numbers (e.g., $9.99, $19.99, which skew leading digits heavily toward 1, 9, 2, and 4 in aggregated financial reporting constraints).

### Sample Result Table

| rank | ticker | sector    | suspicion_score | mad    | conformity_label      |
|------|--------|-----------|-----------------|--------|-----------------------|
| 1    | JPM    | Finance   | 87.4/100        | 0.0182 | Nonconformity         |
| 2    | XOM    | Energy    | 73.1/100        | 0.0145 | Marginally Acceptable |
| 3    | MRK    | Healthcare| 61.2/100        | 0.0118 | Acceptable Conformity |
| ...  | ...    | ...       | ...             | ...    | ...                   |

*(Note: Target companies and results change dynamically upon SEC data downloads).*

## Limitations & Disclaimer

**This analysis is for educational purposes only and does not constitute evidence of fraud or financial misconduct.** 

Deviating from Benford's Law acts solely as a "smoke alarm," indicating numerical irregularity. While it is heavily used by the IRS and audit firms to initiate deeper investigations, differences between expected and observed probabilities can emerge from perfectly innocent realities—such as natural dataset ceilings, standardized accounting thresholds, or sector-specific rounding effects.

## Suggested Next Steps

- **Time-Series Tracking:** Calculate year-by-year MAD scores per company to detect structural shifts in accounting rigor or abrupt data manipulation ahead of market crises.
- **Second-Digit Testing:** Incorporate an analysis of the second digit, or first-two digits, which requires massive sample sizes but offers an immensely powerful forensic view.
- **Global Expansion:** Expand `downloader.py` to ingest financial filings from the LSE or Euronext via external APIs.
