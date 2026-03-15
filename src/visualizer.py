import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import logging
import datetime
from pathlib import Path
from src.benford import BenfordAnalyzer

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

logging.basicConfig(level=logging.INFO, format="%(message)s")

class Visualizer:
    """Class to generate visualizations and PDF reports for Benford's Law analysis."""
    
    def __init__(self, leaderboard_path: Path, charts_dir: Path, reports_dir: Path):
        self.leaderboard_path = leaderboard_path
        self.charts_dir = charts_dir
        self.reports_dir = reports_dir
        
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure we have a dark theme
        plt.style.use('dark_background')
        
        self.df = pd.DataFrame()
        if self.leaderboard_path.exists():
            self.df = pd.read_csv(self.leaderboard_path)

    def generate_benford_curve(self):
        """Generates the theoretical Benford curve reference chart."""
        digits = np.arange(1, 10)
        expected = BenfordAnalyzer.EXPECTED_PERCENTAGES
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(digits, expected, color='royalblue', alpha=0.7, label='Expected Frequency')
        ax.plot(digits, expected, color='white', marker='o', linestyle='-', linewidth=2, label='Log Curve')
        
        ax.set_title("Benford's Law — Expected First Digit Distribution", fontsize=16)
        ax.set_xlabel("First Digit", fontsize=12)
        ax.set_ylabel("Frequency (%)", fontsize=12)
        ax.set_xticks(digits)
        ax.grid(axis='y', alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(self.charts_dir / "benford_curve.png", dpi=300)
        plt.close()
        
    def generate_company_overlays(self):
        """Generates observed vs expected grouped bar charts for all companies."""
        if self.df.empty:
            return
            
        digits = np.arange(1, 10)
        expected = BenfordAnalyzer.EXPECTED_PERCENTAGES
        
        for _, row in self.df.iterrows():
            ticker = row['ticker']
            is_reliable = row.get('reliable', True)
            
            # Extract prepended columns
            z_scores = [row[f'Z_digit_{i}'] for i in range(1, 10)]
            observed_props = [row[f'Obs_digit_{i}'] for i in range(1, 10)]
            observed_pct = np.array(observed_props) * 100
            
            fig, ax = plt.subplots(figsize=(10, 6))
            width = 0.35
            
            # Bar colors based on Z-score threshold (> 1.96)
            bar_colors = ['crimson' if z > 1.96 else 'mediumseagreen' for z in z_scores]
            
            ax.bar(digits - width/2, expected, width, color='royalblue', alpha=0.7, label='Expected (%)')
            ax.bar(digits + width/2, observed_pct, width, color=bar_colors, alpha=0.9, label='Observed (%)')
            
            # Annotations for chi2, MAD, p-value
            stats_text = (
                f"Samples: {int(row['n_samples'])}\n"
                f"Chi²: {row['chi2']:.2f} (p={row['p_value']:.4f})\n"
                f"MAD: {row['mad']:.4f}\n"
                f"Conformity: {row['conformity_label']}"
            )
            ax.text(0.95, 0.95, stats_text, transform=ax.transAxes, fontsize=11,
                    verticalalignment='top', horizontalalignment='right',
                    bbox=dict(boxstyle='round', facecolor='black', alpha=0.5, edgecolor='gray'))
            
            ax.set_title(f"{ticker} — Observed vs. Expected Digit Frequencies", fontsize=14)
            ax.set_xlabel("First Digit", fontsize=12)
            ax.set_ylabel("Frequency (%)", fontsize=12)
            ax.set_xticks(digits)
            ax.legend(loc='upper left')
            ax.grid(axis='y', alpha=0.3)
            
            plt.tight_layout()
            if not is_reliable:
                fig.text(0.5, 0.01,
                         "⚠ Low sample count — results may be statistically unreliable",
                         ha='center', fontsize=10, color='orange',
                         transform=fig.transFigure)
            plt.savefig(self.charts_dir / f"company_overlay_{ticker}.png", dpi=300)
            plt.close()

    def generate_leaderboard_heatmap(self):
        """Generates a heatmap of Z-scores where rows are companies and columns are digits."""
        if self.df.empty:
            return
            
        # Prepare data
        z_cols = [f'Z_digit_{i}' for i in range(1, 10)]
        heatmap_data = (
            self.df
            .sort_values('suspicion_score', ascending=False)
            [['ticker'] + z_cols]
            .set_index('ticker')
        )
        # Rename columns to just the digit
        heatmap_data.columns = [str(i) for i in range(1, 10)]
        
        fig, ax = plt.subplots(figsize=(12, 10))
        # Use RdBu_r centered at 1.96 roughly, or just from 0 to max Z
        sns.heatmap(heatmap_data, cmap='RdBu_r', center=1.96, annot=True, fmt=".1f",
                    linewidths=.5, ax=ax, cbar_kws={'label': 'Z-Score'})
        
        ax.set_title("Anomaly Heatmap: First Digit Z-Scores by Company", fontsize=16)
        ax.set_xlabel("Leading Digit", fontsize=12)
        ax.set_ylabel("Company (Sorted by Suspicion Score)", fontsize=12)
        
        plt.tight_layout()
        plt.savefig(self.charts_dir / "leaderboard_heatmap.png", dpi=300)
        plt.close()

    def generate_sector_comparison(self):
        """Generates horizontal bar chart comparing average MAD per sector."""
        if self.df.empty:
            return
            
        sector_mad = self.df.groupby('sector')['mad'].mean().sort_values()
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        colors = plt.cm.viridis(np.linspace(0, 0.8, len(sector_mad)))
        bars = ax.barh(sector_mad.index, sector_mad.values, color=colors)
        
        # Add labels to bars
        for bar in bars:
            width = bar.get_width()
            ax.annotate(f"{width:.4f}",
                        xy=(width, bar.get_y() + bar.get_height() / 2),
                        xytext=(3, 0),  
                        textcoords="offset points",
                        va='center', fontsize=10, color='white')
                        
        # Add vertical span lines for conformity thresholds
        ax.axvline(x=0.006, color='green', linestyle='--', alpha=0.5, label='Close Conformity (<0.006)')
        ax.axvline(x=0.012, color='yellow', linestyle='--', alpha=0.5, label='Acceptable (<0.012)')
        ax.axvline(x=0.015, color='red', linestyle='--', alpha=0.5, label='Nonconformity (>0.015)')
            
        ax.set_title("Average Mean Absolute Deviation (MAD) by Sector", fontsize=16)
        ax.set_xlabel("Average MAD Score", fontsize=12)
        ax.set_ylabel("Sector", fontsize=12)
        ax.legend()
        plt.tight_layout()
        
        plt.savefig(self.charts_dir / "sector_comparison.png", dpi=300)
        plt.close()
        
    def generate_suspicion_scatter(self):
        """Generates a Plotly interactive scatter plot of Chi2 vs MAD."""
        if self.df.empty:
            return
            
        fig = px.scatter(
            self.df, x="chi2", y="mad",
            size="n_samples", color="sector",
            size_max=45,
            hover_name="ticker",
            hover_data={"n_samples": True},
            labels={
                "chi2": "Chi-Square Statistic",
                "mad": "Mean Absolute Deviation (MAD)",
                "sector": "Sector"
            },
            title="Suspicion Scatter: Chi-Square vs. MAD",
            template="plotly_dark"
        )
        
        # Add threshold lines
        fig.add_hline(y=0.015, line_dash="dash", line_color="red", annotation_text="MAD Nonconformity Threshold")
        
        # Threshold for chi-square (95% conf, df=8 -> approx 15.5)
        fig.add_vline(x=15.5, line_dash="dash", line_color="red", annotation_text="Chi2 p=0.05 Threshold")
        
        fig.write_html(self.charts_dir / "suspicion_scatter.html")

    def _add_footer(self, canvas, doc):
        """Adds standard disclaimer footer on every PDF page."""
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.gray)
        disclaimer = "This analysis is for educational purposes only and does not constitute evidence of fraud or financial misconduct."
        canvas.drawCentredString(letter[0] / 2.0, 0.5 * inch, disclaimer)
        canvas.restoreState()

    def generate_reports(self, top_n: int = 5):
        """Generates PDF reports for the top suspicious companies."""
        if self.df.empty:
            return
            
        top_companies = self.df.head(top_n)
        
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        title_style.alignment = 1 # Center
        subtitle_style = styles['Heading2']
        subtitle_style.alignment = 1
        normal_style = styles['Normal']
        
        for _, row in top_companies.iterrows():
            ticker = row['ticker']
            pdf_path = self.reports_dir / f"{ticker}_audit.pdf"
            
            doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
            story = []
            
            # --- Page 1: Cover ---
            story.append(Spacer(1, 2*inch))
            story.append(Paragraph(f"Benford's Law Digital Audit Report", title_style))
            story.append(Spacer(1, 0.5*inch))
            story.append(Paragraph(f"Target Entity: {ticker}", subtitle_style))
            story.append(Paragraph(f"Sector: {row['sector']}", subtitle_style))
            story.append(Spacer(1, 0.5*inch))
            
            date_str = datetime.datetime.now().strftime("%B %d, %Y")
            story.append(Paragraph(f"Date of Analysis: {date_str}", subtitle_style))
            
            story.append(PageBreak())
            
            # --- Page 2: Overlay Chart ---
            story.append(Paragraph(f"1. Digit Frequencies vs Expected", styles['Heading2']))
            img_path = str(self.charts_dir / f"company_overlay_{ticker}.png")
            # We scale the image to fit the page
            try:
                img = Image(img_path, width=6.5*inch, height=4*inch)
                story.append(img)
            except Exception as e:
                logging.warning(f"Could not load chart image for {ticker}: {e}")
                story.append(Paragraph("Chart graphic missing.", normal_style))
            
            story.append(Spacer(1, 0.5*inch))
            story.append(Paragraph(f"Statistical Summary:", styles['Heading3']))
            summary_text = (
                f"<b>Samples extracted:</b> {row['n_samples']}<br/>"
                f"<b>Chi-Square Statistic:</b> {row['chi2']:.2f} (p={row['p_value']:.4f})<br/>"
                f"<b>Mean Absolute Deviation (MAD):</b> {row['mad']:.4f}<br/>"
                f"<b>Conformity Label:</b> {row['conformity_label']}"
            )
            story.append(Paragraph(summary_text, normal_style))
                
            story.append(PageBreak())
            
            # --- Page 3: Z-Score Table ---
            story.append(Paragraph("2. Individual Digit Z-Scores", styles['Heading2']))
            story.append(Spacer(1, 0.2*inch))
            
            table_data = [["Digit", "Observed (%)", "Expected (%)", "Z-Score", "Flagged?"]]
            expected_pct = BenfordAnalyzer.EXPECTED_PERCENTAGES
            
            flagged_list = []
            
            for d in range(1, 10):
                obs = row[f'Obs_digit_{d}'] * 100
                exp = expected_pct[d-1]
                z = row[f'Z_digit_{d}']
                flag = "YES" if z > 1.96 else "NO"
                
                if flag == "YES":
                    # For plain English interpretation
                    diff = ((obs - exp) / exp) * 100 # % difference from theory
                    flagged_list.append((d, obs, z, diff))
                    
                table_data.append([str(d), f"{obs:.1f}%", f"{exp:.1f}%", f"{z:.2f}", flag])
                
            t = Table(table_data, colWidths=[1*inch, 1.5*inch, 1.5*inch, 1*inch, 1*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            story.append(t)
            
            story.append(PageBreak())
            
            # --- Page 4: Interpretation ---
            story.append(Paragraph("3. Executive Interpretation", styles['Heading2']))
            story.append(Spacer(1, 0.2*inch))
            
            if row['conformity_label'] == "Close Conformity":
                interp = f"The reported numeric data for {ticker} shows excellent adherence to Benford's Law. There are no statistically significant deviations that suggest anomalous reporting patterns."
            else:
                interp = f"The reported numeric data for {ticker} shows {row['conformity_label'].lower()} with Benford's Law. "
                if len(flagged_list) > 0:
                    interp += "Specific digits deviated significantly from expectations:<br/><br/>"
                    for d, obs, z, diff in flagged_list:
                        direction = "more" if diff > 0 else "less"
                        interp += f"• The digit <b>{d}</b> appears {abs(diff):.0f}% {direction} often than expected (Z={z:.2f}, statistically significant at >95% confidence).<br/>"
                
                interp += "<br/><b>Conclusion:</b> This analysis highlights numerical patterns that differ from mathematical expectations. This does not confirm fraud, but warrants further investigation from audit teams, specifically focusing on general ledger accounts starting with the flagged digits."
                
            story.append(Paragraph(interp, normal_style))
                
            # Build PDF
            doc.build(story, onFirstPage=self._add_footer, onLaterPages=self._add_footer)
            logging.info(f"Generated PDF report for {ticker}")

def run_visualizer(leaderboard_path: Path, charts_dir: Path, reports_dir: Path):
    logging.info("Generating charts and visualizing data...")
    viz = Visualizer(leaderboard_path, charts_dir, reports_dir)
    
    viz.generate_benford_curve()
    viz.generate_company_overlays()
    viz.generate_leaderboard_heatmap()
    viz.generate_sector_comparison()
    viz.generate_suspicion_scatter()
    
    logging.info("Generating PDF audit reports for highest suspicion companies...")
    viz.generate_reports(top_n=5)

if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent.parent
    ldb = root_dir / "outputs" / "leaderboard.csv"
    charts = root_dir / "outputs" / "charts"
    reports = root_dir / "outputs" / "reports"
    run_visualizer(ldb, charts, reports)
