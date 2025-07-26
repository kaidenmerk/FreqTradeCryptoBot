#!/usr/bin/env python3
"""
Monte Carlo bootstrap analysis of trading results.

Analyzes the probability distribution of drawdowns and returns based on
historical trade R-multiples.

Usage:
    python scripts/mc_bootstrap.py --input reports/trades.csv --simulations 10000
"""

import argparse
import logging
import os
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_r_multiples(csv_file: str) -> List[float]:
    """
    Load R-multiples from exported trades CSV.
    
    Args:
        csv_file: Path to trades CSV file
        
    Returns:
        List of R-multiple values
    """
    try:
        df = pd.read_csv(csv_file)
        
        if "r_multiple" not in df.columns:
            raise ValueError("CSV file must contain 'r_multiple' column")
            
        r_multiples = df["r_multiple"].dropna().tolist()
        
        logger.info(f"Loaded {len(r_multiples)} R-multiples from {csv_file}")
        logger.info(f"Mean R: {np.mean(r_multiples):.3f}")
        logger.info(f"Std R: {np.std(r_multiples):.3f}")
        
        return r_multiples
        
    except Exception as e:
        logger.error(f"Error loading R-multiples: {e}")
        raise


def monte_carlo_simulation(
    r_multiples: List[float],
    num_simulations: int = 10000,
    num_trades: int = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Run Monte Carlo bootstrap simulation.
    
    Args:
        r_multiples: Historical R-multiple values
        num_simulations: Number of simulation runs
        num_trades: Number of trades per simulation (default: len(r_multiples))
        
    Returns:
        Tuple of (final_returns, max_drawdowns, win_rates)
    """
    if num_trades is None:
        num_trades = len(r_multiples)
        
    final_returns = []
    max_drawdowns = []
    win_rates = []
    
    logger.info(f"Running {num_simulations} simulations with {num_trades} trades each...")
    
    for i in range(num_simulations):
        # Bootstrap sample from historical R-multiples
        sampled_returns = np.random.choice(r_multiples, size=num_trades, replace=True)
        
        # Calculate cumulative returns
        cumulative_returns = np.cumsum(sampled_returns)
        
        # Calculate running maximum for drawdown
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = cumulative_returns - running_max
        
        # Store results
        final_returns.append(cumulative_returns[-1])
        max_drawdowns.append(np.min(drawdowns))
        win_rates.append(np.sum(sampled_returns > 0) / len(sampled_returns))
        
        if (i + 1) % 1000 == 0:
            logger.info(f"Completed {i + 1}/{num_simulations} simulations")
    
    return np.array(final_returns), np.array(max_drawdowns), np.array(win_rates)


def analyze_results(
    final_returns: np.ndarray,
    max_drawdowns: np.ndarray,
    win_rates: np.ndarray,
    output_dir: str = "reports",
) -> None:
    """
    Analyze and visualize Monte Carlo results.
    
    Args:
        final_returns: Array of final return values
        max_drawdowns: Array of maximum drawdown values
        win_rates: Array of win rate values
        output_dir: Output directory for plots and reports
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Calculate statistics
    stats_dict = {
        "Final Returns": {
            "mean": np.mean(final_returns),
            "std": np.std(final_returns),
            "5th_percentile": np.percentile(final_returns, 5),
            "25th_percentile": np.percentile(final_returns, 25),
            "median": np.percentile(final_returns, 50),
            "75th_percentile": np.percentile(final_returns, 75),
            "95th_percentile": np.percentile(final_returns, 95),
            "prob_positive": np.sum(final_returns > 0) / len(final_returns),
        },
        "Max Drawdowns": {
            "mean": np.mean(max_drawdowns),
            "std": np.std(max_drawdowns),
            "5th_percentile": np.percentile(max_drawdowns, 5),
            "25th_percentile": np.percentile(max_drawdowns, 25),
            "median": np.percentile(max_drawdowns, 50),
            "75th_percentile": np.percentile(max_drawdowns, 75),
            "95th_percentile": np.percentile(max_drawdowns, 95),
            "prob_exceed_3R": np.sum(max_drawdowns < -3) / len(max_drawdowns),
            "prob_exceed_5R": np.sum(max_drawdowns < -5) / len(max_drawdowns),
        },
        "Win Rates": {
            "mean": np.mean(win_rates),
            "std": np.std(win_rates),
            "5th_percentile": np.percentile(win_rates, 5),
            "25th_percentile": np.percentile(win_rates, 25),
            "median": np.percentile(win_rates, 50),
            "75th_percentile": np.percentile(win_rates, 75),
            "95th_percentile": np.percentile(win_rates, 95),
        },
    }
    
    # Print key statistics
    logger.info("\nMonte Carlo Analysis Results:")
    logger.info("=" * 50)
    
    logger.info(f"Probability of positive returns: {stats_dict['Final Returns']['prob_positive']:.1%}")
    logger.info(f"Expected final return: {stats_dict['Final Returns']['mean']:.2f}R")
    logger.info(f"Expected max drawdown: {stats_dict['Max Drawdowns']['mean']:.2f}R")
    logger.info(f"Probability of >3R drawdown: {stats_dict['Max Drawdowns']['prob_exceed_3R']:.1%}")
    logger.info(f"Probability of >5R drawdown: {stats_dict['Max Drawdowns']['prob_exceed_5R']:.1%}")
    
    # Create visualizations
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle("Monte Carlo Bootstrap Analysis", fontsize=16)
    
    # Plot 1: Final Returns Distribution
    axes[0, 0].hist(final_returns, bins=50, alpha=0.7, edgecolor="black")
    axes[0, 0].axvline(0, color="red", linestyle="--", label="Break-even")
    axes[0, 0].axvline(np.mean(final_returns), color="green", linestyle="-", label="Mean")
    axes[0, 0].set_xlabel("Final Return (R)")
    axes[0, 0].set_ylabel("Frequency")
    axes[0, 0].set_title("Distribution of Final Returns")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Plot 2: Max Drawdowns Distribution
    axes[0, 1].hist(max_drawdowns, bins=50, alpha=0.7, edgecolor="black", color="red")
    axes[0, 1].axvline(-3, color="orange", linestyle="--", label="3R Drawdown")
    axes[0, 1].axvline(-5, color="darkred", linestyle="--", label="5R Drawdown")
    axes[0, 1].axvline(np.mean(max_drawdowns), color="blue", linestyle="-", label="Mean")
    axes[0, 1].set_xlabel("Max Drawdown (R)")
    axes[0, 1].set_ylabel("Frequency")
    axes[0, 1].set_title("Distribution of Maximum Drawdowns")
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Plot 3: Win Rate Distribution
    axes[1, 0].hist(win_rates, bins=50, alpha=0.7, edgecolor="black", color="green")
    axes[1, 0].axvline(0.5, color="red", linestyle="--", label="50% Win Rate")
    axes[1, 0].axvline(np.mean(win_rates), color="blue", linestyle="-", label="Mean")
    axes[1, 0].set_xlabel("Win Rate")
    axes[1, 0].set_ylabel("Frequency")
    axes[1, 0].set_title("Distribution of Win Rates")
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 4: Return vs Drawdown Scatter
    axes[1, 1].scatter(max_drawdowns, final_returns, alpha=0.5, s=1)
    axes[1, 1].axhline(0, color="red", linestyle="--", alpha=0.7)
    axes[1, 1].axvline(-3, color="orange", linestyle="--", alpha=0.7, label="3R DD")
    axes[1, 1].axvline(-5, color="darkred", linestyle="--", alpha=0.7, label="5R DD")
    axes[1, 1].set_xlabel("Max Drawdown (R)")
    axes[1, 1].set_ylabel("Final Return (R)")
    axes[1, 1].set_title("Return vs Maximum Drawdown")
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    plot_file = os.path.join(output_dir, "monte_carlo_analysis.png")
    plt.savefig(plot_file, dpi=300, bbox_inches="tight")
    logger.info(f"Plot saved to: {plot_file}")
    
    # Save detailed statistics
    stats_file = os.path.join(output_dir, "monte_carlo_stats.txt")
    with open(stats_file, "w") as f:
        f.write("Monte Carlo Bootstrap Analysis Results\n")
        f.write("=" * 50 + "\n\n")
        
        for category, stats_data in stats_dict.items():
            f.write(f"{category}:\n")
            f.write("-" * len(category) + "\n")
            for stat_name, value in stats_data.items():
                if "prob" in stat_name or "percentile" not in stat_name:
                    if "prob" in stat_name:
                        f.write(f"  {stat_name}: {value:.1%}\n")
                    else:
                        f.write(f"  {stat_name}: {value:.3f}\n")
                else:
                    f.write(f"  {stat_name}: {value:.3f}\n")
            f.write("\n")
    
    logger.info(f"Detailed statistics saved to: {stats_file}")
    
    # Save raw results
    results_df = pd.DataFrame({
        "final_return": final_returns,
        "max_drawdown": max_drawdowns,
        "win_rate": win_rates,
    })
    
    results_file = os.path.join(output_dir, "monte_carlo_results.csv")
    results_df.to_csv(results_file, index=False)
    logger.info(f"Raw results saved to: {results_file}")


def main() -> None:
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description="Monte Carlo bootstrap analysis")
    
    parser.add_argument(
        "--input",
        type=str,
        default="reports/trades.csv",
        help="Input trades CSV file (default: reports/trades.csv)"
    )
    
    parser.add_argument(
        "--simulations",
        type=int,
        default=10000,
        help="Number of simulations (default: 10000)"
    )
    
    parser.add_argument(
        "--trades",
        type=int,
        help="Number of trades per simulation (default: same as historical)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Output directory (default: reports)"
    )
    
    args = parser.parse_args()
    
    try:
        # Load historical R-multiples
        r_multiples = load_r_multiples(args.input)
        
        if not r_multiples:
            logger.error("No R-multiples found in input file")
            return
            
        # Run Monte Carlo simulation
        final_returns, max_drawdowns, win_rates = monte_carlo_simulation(
            r_multiples=r_multiples,
            num_simulations=args.simulations,
            num_trades=args.trades,
        )
        
        # Analyze and visualize results
        analyze_results(
            final_returns=final_returns,
            max_drawdowns=max_drawdowns,
            win_rates=win_rates,
            output_dir=args.output_dir,
        )
        
        logger.info("Monte Carlo analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Error running Monte Carlo analysis: {e}")
        raise


if __name__ == "__main__":
    main()
