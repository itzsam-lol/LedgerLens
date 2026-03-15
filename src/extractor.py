import re
import csv
import logging
import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from collections import Counter
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(message)s")

class NumberExtractor:
    """Class to extract and process numbers from raw SEC filings for Benford's Law analysis."""

    def __init__(self, raw_data_dir: Path, processed_data_dir: Path):
        """
        Initialize the extractor.

        Args:
            raw_data_dir: Directory containing downloaded raw SEC filings.
            processed_data_dir: Directory to save processed digit distributions.
        """
        self.raw_data_dir = raw_data_dir
        self.processed_data_dir = processed_data_dir
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)

        # Regex to match integers and decimals (e.g., 1500, 3.14, 1,200,000)
        self.number_pattern = re.compile(r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b')

    def clean_html(self, raw_html: str) -> str:
        """
        Strip HTML tags from a string to extract plain text.
        
        Args:
            raw_html: The raw HTML content.
            
        Returns:
            Cleaned text without HTML markup.
        """
        soup = BeautifulSoup(raw_html, "html.parser")
        return soup.get_text(separator=" ", strip=True)

    def extract_numbers(self, text: str) -> list[float]:
        """
        Extract valid numbers from text.
        
        Excludes years (1990-2030), trivial numbers (<10), etc.
        
        Args:
            text: Plain text content.
            
        Returns:
            List of valid numbers as floats.
        """
        matches = self.number_pattern.findall(text)
        valid_numbers = []
        
        current_year = datetime.datetime.now().year
        year_min = current_year - 40
        year_max = current_year + 5
        
        for match in matches:
            # Remove commas
            clean_str = match.replace(',', '')
            try:
                num = float(clean_str)
                # Apply exclusion rules
                # 1. Must be >= 10
                if num < 10:
                    continue
                # 2. Exclude typical years
                if year_min <= num <= year_max and num == int(num):
                    continue
                
                valid_numbers.append(num)
            except ValueError:
                continue
                
        return valid_numbers

    def get_first_digit(self, number: float) -> int:
        """
        Extract the first significant digit of a number using scientific notation
        formatting for robustness against floats of all magnitudes.

        Args:
            number: The numeric value (must be positive and non-zero).

        Returns:
            The first significant digit (1-9) or 0 if invalid.
        """
        if number <= 0:
            return 0
        try:
            # Format in scientific notation and read the first character
            # e.g., 0.0045 -> '4.500e-03' -> first digit is 4
            first_char = f"{number:.10e}"[0]
            d = int(first_char)
            return d if 1 <= d <= 9 else 0
        except (ValueError, IndexError):
            return 0

    def process_ticker(self, ticker: str):
        """
        Process all filings for a single ticker and output its digit distribution.
        
        Args:
            ticker: The stock ticker to process.
        """
        ticker_dir = self.raw_data_dir / "sec-edgar-filings" / ticker / "10-K"
        if not ticker_dir.exists():
            logging.warning(f"[skip] No raw data found for {ticker}")
            return
            
        filing_dirs = [d for d in ticker_dir.iterdir() if d.is_dir()]
        
        combined_digit_counts = {str(d): 0 for d in range(1, 10)}
        per_year_data = [] # List of dicts with year, digit, count
        
        for fdir in filing_dirs:
            # SEC Edgar creates full submission text file in primary_document.txt or full-text.txt
            # usually full-submission.txt
            file_path = fdir / "full-submission.txt"
            if not file_path.exists():
                # fallback for older downloader versions
                files = list(fdir.glob("*.txt"))
                if not files:
                    continue
                file_path = files[0]
                
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        content = f.read()
                except Exception as e:
                    logging.error(f"[X] Could not read {file_path}: {e}")
                    continue
                    
            text = self.clean_html(content)
            numbers = self.extract_numbers(text)
            
            # Use the folder name as a proxy for the filing year/id
            year_id = fdir.name.split('-')[1] if '-' in fdir.name else fdir.name
            
            year_digit_counts = {str(d): 0 for d in range(1, 10)}
            
            for num in numbers:
                first_digit = self.get_first_digit(num)
                if 1 <= first_digit <= 9:
                    year_digit_counts[str(first_digit)] += 1
                    combined_digit_counts[str(first_digit)] += 1
                    
            for digit in range(1, 10):
                per_year_data.append({
                    "year": year_id,
                    "digit": digit,
                    "count": year_digit_counts[str(digit)]
                })
        
        # Save to CSV
        if per_year_data:
            out_file = self.processed_data_dir / f"{ticker}_digits.csv"
            with open(out_file, "w", newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["year", "digit", "count"])
                writer.writeheader()
                writer.writerows(per_year_data)
                
            total_nums = sum(combined_digit_counts.values())
            logging.info(f"[✓] Extracted {total_nums} valid numbers for {ticker}")
            
            if total_nums < 300:
                logging.warning(
                    f"[!] {ticker} only yielded {total_nums} valid numbers. "
                    f"Benford analysis requires a large sample — results may be unreliable. "
                    f"Consider this ticker's results with caution."
                )

def run_extractor(raw_data_dir: Path, processed_data_dir: Path, dry_run: bool = False, specific_ticker: str = None):
    """
    Main entry point for the extraction step.
    
    Args:
        raw_data_dir: Path to raw SEC data.
        processed_data_dir: Path to save output CSVs.
        dry_run: Run in dry-run mode.
        specific_ticker: Specific ticker if provided.
    """
    from src.downloader import ALL_TICKERS
    
    target_tickers = ALL_TICKERS
    if specific_ticker:
        target_tickers = [specific_ticker.upper()]
    elif dry_run:
        target_tickers = ["AAPL", "JPM", "WMT"]
        
    extractor = NumberExtractor(raw_data_dir, processed_data_dir)
    
    logging.info("Starting extraction process...")
    for ticker in tqdm(target_tickers, desc="Extracting numbers"):
        extractor.process_ticker(ticker)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (test 3 companies)")
    parser.add_argument("--ticker", type=str, help="Specific ticker to run")
    args = parser.parse_args()
    
    root_dir = Path(__file__).resolve().parent.parent
    raw_dir = root_dir / "data" / "raw"
    processed_dir = root_dir / "data" / "processed"
    run_extractor(raw_dir, processed_dir, dry_run=args.dry_run, specific_ticker=args.ticker)
