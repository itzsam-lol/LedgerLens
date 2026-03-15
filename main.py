import argparse
import logging
import time
import sys
import pandas as pd
from pathlib import Path

# Local imports
from src.downloader import run_downloader, ALL_TICKERS
from src.extractor import run_extractor
from src.scorer import run_scorer
from src.visualizer import Visualizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_args():
    parser = argparse.ArgumentParser(description="Benford's Law Digital Audit pipeline for SEC filings.")
    parser.add_argument("--download", action="store_true", help="Run the SEC EDGAR downloader.")
    parser.add_argument("--extract", action="store_true", help="Parse HTML and extract numbers.")
    parser.add_argument("--analyze", action="store_true", help="Run Benford stats and composite scoring.")
    parser.add_argument("--visualize", action="store_true", help="Generate all analytical charts.")
    parser.add_argument("--report", action="store_true", help="Generate PDF reports for top suspicious companies.")
    parser.add_argument("--all", action="store_true", help="Run the full pipeline end-to-end.")
    parser.add_argument("--ticker", type=str, help="Run targeted pipeline for a single company (e.g., AAPL).")
    parser.add_argument("--dry-run", action="store_true", help="Run the pipeline on a restricted 3-company dataset for testing.")
    return parser.parse_args()

def main():
    args = get_args()
    
    # Base paths
    root_dir = Path(__file__).resolve().parent
    raw_dir = root_dir / "data" / "raw"
    processed_dir = root_dir / "data" / "processed"
    outputs_dir = root_dir / "outputs"
    charts_dir = outputs_dir / "charts"
    reports_dir = outputs_dir / "reports"
    
    # If no flags passed, print help and exit
    if not any([args.download, args.extract, args.analyze, args.visualize, args.report, args.all]):
        logging.warning("No action specified. Use --help to see available options.")
        return

    # Determine tickers to process
    target_tickers = ALL_TICKERS
    if args.ticker:
        target_tickers = [args.ticker.upper()]
    elif args.dry_run:
        logging.info("[DRY RUN] Overriding target to AAPL, JPM, WMT")
        target_tickers = ["AAPL", "JPM", "WMT"]

    start_time = time.time()
    
    try:
        if args.all or args.download:
            logging.info("=== STEP 1: DOWNLOADING DATA ===")
            run_downloader(raw_dir, dry_run=args.dry_run, specific_ticker=args.ticker)

        if args.all or args.extract:
            logging.info("=== STEP 2: NUMBER EXTRACTION ===")
            run_extractor(raw_dir, processed_dir, dry_run=args.dry_run, specific_ticker=args.ticker)

        if args.all or args.analyze:
            logging.info("=== STEP 3: BENFORD ANALYSIS & SCORING ===")
            run_scorer(processed_dir, outputs_dir, dry_run=args.dry_run, specific_ticker=args.ticker)

        # Setup Visualizer instance if we need to do viz or reporting
        viz = None
        if args.all or args.visualize or args.report:
            leaderboard_path = outputs_dir / "leaderboard.csv"
            if leaderboard_path.exists():
                viz = Visualizer(leaderboard_path, charts_dir, reports_dir)
            else:
                logging.error("Cannot visualize — leaderboard.csv missing. Run: python main.py --analyze first.")
                sys.exit(1)

        if viz and (args.all or args.visualize):
            logging.info("=== STEP 4: GENERATING VISUALIZATIONS ===")
            viz.generate_benford_curve()
            viz.generate_company_overlays()
            viz.generate_leaderboard_heatmap()
            viz.generate_sector_comparison()
            viz.generate_suspicion_scatter()
            logging.info("[✓] Charts saved to outputs/charts/")

        if viz and (args.all or args.report):
            logging.info("=== STEP 5: GENERATING REPORTS ===")
            if args.ticker:
                # Top report if only one company selected
                viz.generate_reports(top_n=1)
            elif args.dry_run:
                viz.generate_reports(top_n=3)
            else:
                viz.generate_reports(top_n=5)
            logging.info("[✓] PDF Reports saved to outputs/reports/")
            
    except Exception as e:
        logging.error(f"Pipeline execution failed: {e}", exc_info=True)
    finally:
        elapsed = time.time() - start_time
        logging.info(f"Pipeline finished in {elapsed:.2f} seconds.")
        
        # Determine summary statistics if analyze was run
        leaderboard_path = outputs_dir / "leaderboard.csv"
        if leaderboard_path.exists():
            df = pd.read_csv(leaderboard_path)
            total = len(df)
            flagged = len(df[df['conformity_label'].str.contains("Nonconformity")])
            top3 = ", ".join(df['ticker'].head(3).tolist())
            logging.info(f"--- SUMMARY ---")
            logging.info(f"Companies Analyzed: {total}")
            logging.info(f"Flagged as Nonconforming: {flagged}")
            logging.info(f"Top Suspicious Tickers: {top3}")

if __name__ == "__main__":
    main()
