#!/usr/bin/env python3
"""
Monte Carlo Bootstrap Analysis for Freqtrade

Performs Monte Carlo simulation on historical trade results to estimate
future performance distributions, drawdown probabilities, and risk metrics.

Usage:
    python scripts/mc_bootstrap.py --trades reports/trades_export.csv
    python scripts/mc_bootstrap.py --trades reports/trades_export.csv --simulations 10000
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_trade_data(file_path: str) -> pd.DataFrame:
    """Load trade data from CSV file."""
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Loaded {len(df)} trades from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading trade data: {e}")
        raise


def prepare_returns_data(df: pd.DataFrame) -> np.ndarray:
    """
    Prepare returns data for Monte Carlo simulation.
    
    Args:
        df: DataFrame with trade data
        
    Returns:
        Array of trade returns (R-multiples or profit percentages)
    """
    try:
        # Filter to closed trades only
        closed_trades = df[df['is_open'] == 0].copy()
        
        if len(closed_trades) == 0:
            raise ValueError("No closed trades found")
        
        # Use R-multiples if available, otherwise profit percentages
        if 'r_multiple' in closed_trades.columns:
            returns = closed_trades['r_multiple'].dropna().values
            logger.info(f"Using R-multiples for {len(returns)} trades")
        else:
            returns = closed_trades['close_profit'].dropna().values
            logger.info(f"Using profit percentages for {len(returns)} trades")
        
        if len(returns) == 0:
            raise ValueError("No valid returns data found")
        
        logger.info(f"Returns statistics:")
        logger.info(f"  Mean: {np.mean(returns):.3f}")
        logger.info(f"  Std: {np.std(returns):.3f}")
        logger.info(f"  Min: {np.min(returns):.3f}")  
        logger.info(f"  Max: {np.max(returns):.3f}")
        
        return returns
        
    except Exception as e:
        logger.error(f"Error preparing returns data: {e}")
        raise


def run_monte_carlo_simulation(
    returns: np.ndarray,
    num_simulations: int = 5000,
    num_trades_per_sim: int = None
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Run Monte Carlo bootstrap simulation.
    
    Args:
        returns: Array of historical trade returns
        num_simulations: Number of simulation runs
        num_trades_per_sim: Number of trades per simulation (default: len(returns))
        
    Returns:
        Tuple of (final_returns, max_drawdowns, equity_curves)
    """
    try:
        if num_trades_per_sim is None:
            num_trades_per_sim = len(returns)
        
        logger.info(f"Running {num_simulations} simulations with {num_trades_per_sim} trades each")
        
        final_returns = np.zeros(num_simulations)
        max_drawdowns = np.zeros(num_simulations)
        equity_curves = np.zeros((num_simulations, num_trades_per_sim + 1))
        
        for i in range(num_simulations):
            # Bootstrap sample from historical returns
            sim_returns = np.random.choice(returns, size=num_trades_per_sim, replace=True)
            
            # Calculate cumulative equity curve
            equity_curve = np.concatenate([[0], np.cumsum(sim_returns)])
            equity_curves[i] = equity_curve
            
            # Final return
            final_returns[i] = equity_curve[-1]
            
            # Calculate maximum drawdown
            running_max = np.maximum.accumulate(equity_curve)
            drawdown = equity_curve - running_max
            max_drawdowns[i] = np.min(drawdown)
            
            if (i + 1) % 1000 == 0:
                logger.info(f"Completed {i + 1} simulations")
        
        logger.info("Monte Carlo simulation completed")
        return final_returns, max_drawdowns, equity_curves
        
    except Exception as e:
        logger.error(f"Error in Monte Carlo simulation: {e}")
        raise


def analyze_simulation_results(
    final_returns: np.ndarray,
    max_drawdowns: np.ndarray,
    returns: np.ndarray
) -> Dict:
    """Analyze Monte Carlo simulation results."""
    try:
        results = {}
        
        # Final return statistics
        results['final_return_mean'] = np.mean(final_returns)
        results['final_return_median'] = np.median(final_returns)
        results['final_return_std'] = np.std(final_returns)
        results['final_return_5th_percentile'] = np.percentile(final_returns, 5)
        results['final_return_95th_percentile'] = np.percentile(final_returns, 95)
        
        # Probability of positive returns
        results['prob_positive_return'] = np.mean(final_returns > 0) * 100
        
        # Drawdown statistics
        results['max_drawdown_mean'] = np.mean(max_drawdowns)
        results['max_drawdown_median'] = np.median(max_drawdowns)
        results['max_drawdown_std'] = np.std(max_drawdowns)
        results['max_drawdown_5th_percentile'] = np.percentile(max_drawdowns, 5)
        results['max_drawdown_95th_percentile'] = np.percentile(max_drawdowns, 95)
        
        # Risk metrics (assuming R-multiples)
        if np.mean(returns) > 0:  # Check if using R-multiples
            results['prob_drawdown_gt_3R'] = np.mean(max_drawdowns < -3) * 100
            results['prob_drawdown_gt_5R'] = np.mean(max_drawdowns < -5) * 100
            results['prob_drawdown_gt_10R'] = np.mean(max_drawdowns < -10) * 100
        
        # Value at Risk (VaR)
        results['var_5_percent'] = np.percentile(final_returns, 5)
        results['var_1_percent'] = np.percentile(final_returns, 1)
        
        # Expected shortfall (Conditional VaR)
        var_5 = results['var_5_percent']
        results['expected_shortfall_5_percent'] = np.mean(final_returns[final_returns <= var_5])
        
        return results
        
    except Exception as e:
        logger.error(f"Error analyzing results: {e}")
        return {}


def create_visualizations(
    final_returns: np.ndarray,
    max_drawdowns: np.ndarray,
    equity_curves: np.ndarray,
    output_dir: str = "reports"
):
    """Create visualization plots."""
    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Set style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # 1. Final Returns Distribution
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Returns histogram
        axes[0, 0].hist(final_returns, bins=50, alpha=0.7, edgecolor='black')
        axes[0, 0].axvline(np.mean(final_returns), color='red', linestyle='--', 
                          label=f'Mean: {np.mean(final_returns):.2f}')
        axes[0, 0].axvline(np.median(final_returns), color='orange', linestyle='--',
                          label=f'Median: {np.median(final_returns):.2f}')
        axes[0, 0].set_xlabel('Final Return (R-multiples)')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('Distribution of Final Returns')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Drawdown histogram
        axes[0, 1].hist(max_drawdowns, bins=50, alpha=0.7, color='red', edgecolor='black')
        axes[0, 1].axvline(np.mean(max_drawdowns), color='darkred', linestyle='--',
                          label=f'Mean: {np.mean(max_drawdowns):.2f}')
        axes[0, 1].axvline(np.median(max_drawdowns), color='orange', linestyle='--',
                          label=f'Median: {np.median(max_drawdowns):.2f}')
        axes[0, 1].set_xlabel('Maximum Drawdown (R-multiples)')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].set_title('Distribution of Maximum Drawdown')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # Scatter plot: Returns vs Drawdown
        axes[1, 0].scatter(max_drawdowns, final_returns, alpha=0.5, s=1)
        axes[1, 0].set_xlabel('Maximum Drawdown')
        axes[1, 0].set_ylabel('Final Return')
        axes[1, 0].set_title('Returns vs Drawdown')
        axes[1, 0].grid(True, alpha=0.3)
        
        # Sample equity curves
        sample_indices = np.random.choice(len(equity_curves), size=min(100, len(equity_curves)), replace=False)
        for i in sample_indices:
            axes[1, 1].plot(equity_curves[i], alpha=0.1, color='blue', linewidth=0.5)
        
        # Add percentile curves
        percentiles = [5, 25, 50, 75, 95]
        colors = ['red', 'orange', 'green', 'orange', 'red']
        for p, color in zip(percentiles, colors):
            curve = np.percentile(equity_curves, p, axis=0)
            axes[1, 1].plot(curve, color=color, linewidth=2, label=f'{p}th percentile')
        
        axes[1, 1].set_xlabel('Trade Number')
        axes[1, 1].set_ylabel('Cumulative Return (R-multiples)')
        axes[1, 1].set_title('Sample Equity Curves')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path / 'monte_carlo_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Risk Analysis Plot
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # QQ plot for returns
        stats.probplot(final_returns, dist="norm", plot=axes[0])
        axes[0].set_title('Q-Q Plot: Final Returns vs Normal Distribution')
        axes[0].grid(True, alpha=0.3)
        
        # Drawdown probability plot
        drawdown_thresholds = np.arange(-1, -20, -1)
        probabilities = [np.mean(max_drawdowns <= threshold) * 100 for threshold in drawdown_thresholds]
        
        axes[1].plot(-drawdown_thresholds, probabilities, marker='o', linewidth=2, markersize=6)
        axes[1].set_xlabel('Drawdown Threshold (R-multiples)')
        axes[1].set_ylabel('Probability (%)')
        axes[1].set_title('Probability of Exceeding Drawdown Thresholds')
        axes[1].grid(True, alpha=0.3)
        axes[1].invert_xaxis()
        
        plt.tight_layout()
        plt.savefig(output_path / 'monte_carlo_risk_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Visualizations saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Error creating visualizations: {e}")


def main():
    """Main function to handle command line arguments and execute analysis."""
    parser = argparse.ArgumentParser(
        description="Monte Carlo bootstrap analysis for Freqtrade trades",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--trades",
        default="reports/trades_export.csv",
        help="Path to trades CSV file"
    )
    
    parser.add_argument(
        "--simulations",
        type=int,
        default=5000,
        help="Number of Monte Carlo simulations"
    )
    
    parser.add_argument(
        "--trades-per-sim",
        type=int,
        help="Number of trades per simulation (default: same as historical)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Output directory for results and plots"
    )
    
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip generating plots"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load trade data
        logger.info(f"Loading trade data from: {args.trades}")
        df = load_trade_data(args.trades)
        
        # Prepare returns data
        returns = prepare_returns_data(df)
        
        # Run Monte Carlo simulation
        final_returns, max_drawdowns, equity_curves = run_monte_carlo_simulation(
            returns, args.simulations, args.trades_per_sim
        )
        
        # Analyze results
        results = analyze_simulation_results(final_returns, max_drawdowns, returns)
        
        # Print results
        logger.info("\n" + "="*60)
        logger.info("MONTE CARLO SIMULATION RESULTS")
        logger.info("="*60)
        
        logger.info(f"Simulations run: {args.simulations}")
        logger.info(f"Trades per simulation: {len(returns) if args.trades_per_sim is None else args.trades_per_sim}")
        logger.info("")
        
        logger.info("FINAL RETURN STATISTICS:")
        logger.info(f"  Mean: {results.get('final_return_mean', 0):.3f}")
        logger.info(f"  Median: {results.get('final_return_median', 0):.3f}")
        logger.info(f"  Standard Deviation: {results.get('final_return_std', 0):.3f}")
        logger.info(f"  5th Percentile: {results.get('final_return_5th_percentile', 0):.3f}")
        logger.info(f"  95th Percentile: {results.get('final_return_95th_percentile', 0):.3f}")
        logger.info(f"  Probability of Positive Return: {results.get('prob_positive_return', 0):.1f}%")
        logger.info("")
        
        logger.info("DRAWDOWN STATISTICS:")
        logger.info(f"  Mean Max Drawdown: {results.get('max_drawdown_mean', 0):.3f}")
        logger.info(f"  Median Max Drawdown: {results.get('max_drawdown_median', 0):.3f}")
        logger.info(f"  5th Percentile (Worst): {results.get('max_drawdown_5th_percentile', 0):.3f}")
        
        if 'prob_drawdown_gt_3R' in results:
            logger.info(f"  Probability of Drawdown > 3R: {results['prob_drawdown_gt_3R']:.1f}%")
            logger.info(f"  Probability of Drawdown > 5R: {results['prob_drawdown_gt_5R']:.1f}%")
            logger.info(f"  Probability of Drawdown > 10R: {results['prob_drawdown_gt_10R']:.1f}%")
        
        logger.info("")
        logger.info("RISK METRICS:")
        logger.info(f"  VaR (5%): {results.get('var_5_percent', 0):.3f}")
        logger.info(f"  VaR (1%): {results.get('var_1_percent', 0):.3f}")
        logger.info(f"  Expected Shortfall (5%): {results.get('expected_shortfall_5_percent', 0):.3f}")
        
        # Save results to file
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        results_file = output_path / 'monte_carlo_results.json'
        import json
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to: {results_file}")
        
        # Create visualizations
        if not args.no_plots:
            logger.info("Creating visualizations...")
            create_visualizations(final_returns, max_drawdowns, equity_curves, args.output_dir)
        
        logger.info("Monte Carlo analysis completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
