import time
import os
from pathlib import Path
from sec_edgar_downloader import Downloader
import logging

# Configure basic logging for the module
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Hardcoded companies by sector
COMPANIES = {
    "Technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "INTC"],
    "Finance": ["JPM", "BAC", "GS", "WFC", "MS", "C"],
    "Retail": ["WMT", "TGT", "AMZN", "COST", "HD", "LOW"],
    "Healthcare": ["JNJ", "PFE", "MRK", "ABT", "UNH", "CVS"],
    "Energy": ["XOM", "CVX", "BP", "COP", "SLB", "HAL"]
}

# Flatten the list of all tickers
ALL_TICKERS = [ticker for sector_tickers in COMPANIES.values() for ticker in sector_tickers]

class SECDownloader:
    """Class to handle downloading of SEC 10-K filings."""

    def __init__(self, raw_data_dir: Path, user_agent: str = "LedgerLensProject (your.email@example.com)"):
        """
        Initialize the downloader.

        Args:
            raw_data_dir: The directory where raw downloaded filings should be saved.
            user_agent: The User-Agent string required by SEC EDGAR.
        """
        self.raw_data_dir = raw_data_dir
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        # Assuming you provide a valid user agent
        # The syntax for sec-edgar-downloader >= 5.0.0 requires company name and email
        user_email = os.getenv("LEDGERLENS_EMAIL", "test@example.com")
        if user_email == "test@example.com":
            logging.warning(
                "[!] SEC EDGAR requires a valid email in the User-Agent. "
                "Set the LEDGERLENS_EMAIL environment variable to avoid being rate-limited. "
                "Example: export LEDGERLENS_EMAIL=your@email.com"
            )
        self.dl = Downloader("LedgerLensApp", user_email, self.raw_data_dir)

    def download_10k_filings(self, ticker: str, num_filings: int = 10, dry_run: bool = False):
        """
        Download 10-K filings for a specific ticker.

        Args:
            ticker: The stock ticker (e.g., 'AAPL').
            num_filings: Number of latest filings to download.
            dry_run: If True, prints what would be downloaded without actually downloading.
        """
        ticker = ticker.upper()
        ticker_dir = self.raw_data_dir / "sec-edgar-filings" / ticker / "10-K"
        
        # Determine how many exist already
        existing_filings = 0
        if ticker_dir.exists():
            existing_filings = len(list(ticker_dir.iterdir()))

        if existing_filings >= num_filings:
            logging.info(f"[skip] {ticker} already has {existing_filings} 10-K filings downloaded.")
            return

        if dry_run:
            logging.info(f"[dry-run] Would download up to {num_filings} 10-K filings for {ticker}.")
            return

        logging.info(f"Downloading 10-K filings for {ticker}...")
        try:
            # Download the latest N 10-K filings
            self.dl.get("10-K", ticker, limit=num_filings)
            logging.info(f"[✓] Successfully processed request for {ticker}.")
            
            # Rate limiting as required by SEC EDGAR (at least 0.1s, 0.5s is safer)
            time.sleep(0.5)
            
            # Verify files were actually downloaded
            downloaded_count = len(list(ticker_dir.iterdir())) if ticker_dir.exists() else 0
            if downloaded_count == 0:
                logging.warning(f"[!] {ticker}: Download completed but no files found in {ticker_dir}. "
                                f"Check your LEDGERLENS_EMAIL or SEC EDGAR connectivity.")
            else:
                logging.info(f"[✓] {ticker}: {downloaded_count} filing(s) confirmed on disk.")
            
        except Exception as e:
            logging.error(f"[X] Failed to download data for {ticker}. Error: {e}")

def run_downloader(raw_data_dir: Path, dry_run: bool = False, specific_ticker: str = None):
    """
    Main entry point for the download step.
    
    Args:
        raw_data_dir: Path to save the downloaded filings.
        dry_run: Run in dry-run mode (only targets 3 companies, or skips actual dl).
        specific_ticker: If provided, only download for this ticker.
    """
    downloader = SECDownloader(raw_data_dir=raw_data_dir)
    
    target_tickers = ALL_TICKERS
    
    if specific_ticker:
        target_tickers = [specific_ticker.upper()]
    elif dry_run:
        logging.info("Dry-run mode: Selecting only 3 companies for testing.")
        target_tickers = ["AAPL", "JPM", "WMT"]

    for ticker in target_tickers:
        downloader.download_10k_filings(ticker, num_filings=10)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (test 3 companies)")
    parser.add_argument("--ticker", type=str, help="Specific ticker to run")
    args = parser.parse_args()
    
    base_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    run_downloader(base_dir, dry_run=args.dry_run, specific_ticker=args.ticker)
