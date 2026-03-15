import pandas as pd
import logging
from pathlib import Path
from tabulate import tabulate
from src.benford import BenfordAnalyzer

logging.basicConfig(level=logging.INFO, format="%(message)s")

class Scorer:
    """Class to aggregate Benford analysis results and rank companies by suspicion score."""
    
    def __init__(self, processed_data_dir: Path, output_dir: Path):
        self.processed_data_dir = processed_data_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.analyzer = BenfordAnalyzer()

    def process_all(self, target_tickers: list[str]) -> pd.DataFrame:
        """
        Process all extracted data and compile a leaderboard DataFrame.
        """
        from src.downloader import COMPANIES
        
        # Reverse mapping from ticker to sector
        ticker_to_sector = {}
        for sector, tickers in COMPANIES.items():
            for t in tickers:
                ticker_to_sector[t] = sector

        results = []
        for ticker in target_tickers:
            csv_path = self.processed_data_dir / f"{ticker}_digits.csv"
            if not csv_path.exists():
                continue
                
            df = pd.read_csv(csv_path)
            # Combine across all years
            analysis = self.analyzer.analyze_company(df)
            
            # Save Z-scores mapping for the heatmap
            z_scores_dict = {f"Z_digit_{i+1}": analysis["digit_zscores"][i] for i in range(9)}
            obs_dict = {f"Obs_digit_{i+1}": analysis["observed_proportions"][i] for i in range(9)}
            
            record = {
                "ticker": ticker,
                "sector": ticker_to_sector.get(ticker, "Unknown"),
                "chi2": analysis["chi2"],
                "p_value": analysis["p_value"],
                "mad": analysis["mad"],
                "conformity_label": analysis["conformity_label"],
                "flagged_digits": analysis["flagged_digits"],
                "n_samples": analysis["n_samples"],
                **z_scores_dict,
                **obs_dict
            }
            results.append(record)
            
        return pd.DataFrame(results)

    def generate_leaderboard(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute composite suspicion score and generate ranked leaderboard.
        Score = 40% normalized chi2 + 40% normalized MAD + 20% normalized flagged_digits
        """
        if df.empty:
            logging.warning("No data available to generate leaderboard.")
            return df
            
        # Normalize columns via Min-Max scaling
        def min_max_scale(series):
            if series.max() == series.min():
                return series * 0
            return (series - series.min()) / (series.max() - series.min())

        df["norm_chi2"] = min_max_scale(df["chi2"])
        df["norm_mad"] = min_max_scale(df["mad"])
        df["norm_flags"] = min_max_scale(df["flagged_digits"])

        # Composite score 0-100
        df["suspicion_score"] = (df["norm_chi2"] * 0.4 + 
                                 df["norm_mad"] * 0.4 + 
                                 df["norm_flags"] * 0.2) * 100

        # Create the final leaderboard view
        leaderboard = df.sort_values(by="suspicion_score", ascending=False).reset_index(drop=True)
        leaderboard["rank"] = leaderboard.index + 1
        
        # Keep detailed columns but reorder for clarity
        cols_front = ["rank", "ticker", "sector", "suspicion_score", "mad", "chi2", "p_value", "conformity_label", "flagged_digits", "n_samples"]
        cols_z = [f"Z_digit_{i}" for i in range(1, 10)]
        cols_obs = [f"Obs_digit_{i}" for i in range(1, 10)]
        
        leaderboard = leaderboard[cols_front + cols_z + cols_obs]
        
        # Save to outputs
        leaderboard.to_csv(self.output_dir / "leaderboard.csv", index=False)
        return leaderboard

    def print_leaderboard(self, leaderboard: pd.DataFrame):
        """Prints a clean formatted table to console."""
        if leaderboard.empty:
            return
            
        print("\n🏆 Suspicion Leaderboard (Top 15) 🏆")
        display_cols = ["rank", "ticker", "sector", "suspicion_score", "mad", "conformity_label", "flagged_digits", "n_samples"]
        
        # Format columns for display
        df_disp = leaderboard.head(15)[display_cols].copy()
        df_disp["suspicion_score"] = df_disp["suspicion_score"].apply(lambda x: f"{x:.1f}/100")
        df_disp["mad"] = df_disp["mad"].apply(lambda x: f"{x:.4f}")
        
        print(tabulate(df_disp, headers="keys", tablefmt="heavy_grid", showindex=False))

def run_scorer(processed_data_dir: Path, output_dir: Path, dry_run: bool = False, specific_ticker: str = None):
    from src.downloader import ALL_TICKERS
    
    target_tickers = ALL_TICKERS
    if specific_ticker:
        target_tickers = [specific_ticker.upper()]
    elif dry_run:
        target_tickers = ["AAPL", "JPM", "WMT"]
        
    scorer = Scorer(processed_data_dir, output_dir)
    logging.info("Calculating deviation metrics and ranking companies...")
    df_raw = scorer.process_all(target_tickers)
    leaderboard = scorer.generate_leaderboard(df_raw)
    scorer.print_leaderboard(leaderboard)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ticker", type=str)
    args = parser.parse_args()
    
    root_dir = Path(__file__).resolve().parent.parent
    processed_dir = root_dir / "data" / "processed"
    out_dir = root_dir / "outputs"
    run_scorer(processed_dir, out_dir, dry_run=args.dry_run, specific_ticker=args.ticker)
