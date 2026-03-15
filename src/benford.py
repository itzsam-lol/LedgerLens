import pandas as pd
import numpy as np
from scipy.stats import chisquare
from typing import Dict, Any

class BenfordAnalyzer:
    """Class to perform Benford's Law analysis on extracted number distributions."""

    # Theoretical Benford's Law first digit expected proportions
    # P(d) = log10(1 + 1/d)
    EXPECTED_PROPORTIONS = np.array([np.log10(1 + 1/d) for d in range(1, 10)])
    EXPECTED_PERCENTAGES = EXPECTED_PROPORTIONS * 100

    @staticmethod
    def get_mad_conformity_label(mad: float) -> str:
        """
        Get standard forensic accounting conformity label based on MAD value.
        """
        if mad < 0.006:
            return "Close Conformity"
        elif mad <= 0.012:
            return "Acceptable Conformity"
        elif mad <= 0.015:
            return "Marginally Acceptable"
        else:
            return "Nonconformity"

    def analyze_company(self, combined_distribution: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze a company's digit distribution against Benford's Law.
        
        Args:
            combined_distribution: DataFrame with columns 'digit' and 'count' representing
                                   the aggregated frequencies across all years.
                                   
        Returns:
            Dictionary containing chi2, p_value, mad, z_scores, etc.
        """
        # Ensure we have all digits 1-9 sorted
        df = combined_distribution.groupby('digit')['count'].sum().reset_index()
        df = df.set_index('digit').reindex(range(1, 10), fill_value=0).reset_index()
        
        observed_counts = df['count'].values
        total_samples = np.sum(observed_counts)
        
        if total_samples == 0:
            return {
                "chi2": np.nan, "p_value": np.nan, "mad": np.nan,
                "digit_zscores": [np.nan] * 9, "conformity_label": "No Data",
                "n_samples": 0, "flagged_digits": 0,
                "observed_proportions": [0.0] * 9,
                "reliable": False
            }
            
        MIN_RELIABLE_SAMPLES = 100
        if total_samples < MIN_RELIABLE_SAMPLES:
            import logging
            logging.warning(
                f"[!] Only {total_samples} samples available. Chi-Square results are unreliable "
                f"below {MIN_RELIABLE_SAMPLES} samples. Interpret with caution."
            )
        observed_proportions = observed_counts / total_samples
        expected_counts = self.EXPECTED_PROPORTIONS * total_samples
        
        # 1. Chi-Square Test
        # We need to handle zero expected counts theoretically, but Benford probabilities > 0
        chi2_stat, p_value = chisquare(f_obs=observed_counts, f_exp=expected_counts)
        
        # 2. Mean Absolute Deviation (MAD)
        mad = np.sum(np.abs(observed_proportions - self.EXPECTED_PROPORTIONS)) / 9.0
        conformity_label = self.get_mad_conformity_label(mad)
        
        # 3. Z-scores for individual digits
        # Z = |obs_prop - exp_prop| / sqrt(exp_prop * (1 - exp_prop) / n)
        z_scores = []
        flagged_digits = 0
        for i in range(9):
            p = self.EXPECTED_PROPORTIONS[i]
            obs_p = observed_proportions[i]
            # Standard error
            se = np.sqrt(p * (1 - p) / total_samples)
            if se == 0:
                z = 0.0
            else:
                z = np.abs(obs_p - p) / se
            
            z_scores.append(z)
            if z > 1.96:
                flagged_digits += 1
                
        return {
            "chi2": float(chi2_stat),
            "p_value": float(p_value),
            "mad": float(mad),
            "digit_zscores": [float(z) for z in z_scores],
            "conformity_label": conformity_label,
            "n_samples": int(total_samples),
            "flagged_digits": int(flagged_digits),
            "observed_proportions": [float(p) for p in observed_proportions],
            "reliable": total_samples >= MIN_RELIABLE_SAMPLES
        }
