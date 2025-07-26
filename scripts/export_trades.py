#!/usr/bin/env python3
"""
Export trades from Freqtrade database to CSV with R-multiples calculation.

Usage:
    python scripts/export_trades.py --db-url sqlite:///user_data/trades.sqlite --output trades.csv
"""

import argparse
import logging
import os
import sqlite3
from datetime import datetime
from typing import Optional

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_trades_from_db(db_url: str) -> pd.DataFrame:
    """
    Load trades from SQLite database.
    
    Args:
        db_url: Database URL (e.g., 'sqlite:///user_data/trades.sqlite')
        
    Returns:
        DataFrame with trade data
    """
    # Extract SQLite file path from URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
    else:
        raise ValueError(f"Unsupported database URL: {db_url}")
        
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")
    
    # Connect to database and load trades
    try:
        conn = sqlite3.connect(db_path)
        
        query = """
        SELECT 
            id,
            exchange,
            pair,
            is_open,
            fee_open,
            fee_close,
            open_rate,
            close_rate,
            amount,
            stake_amount,
            close_profit,
            close_profit_abs,
            trade_duration,
            open_date,
            close_date,
            open_order_id,
            strategy,
            enter_tag,
            exit_reason
        FROM trades
        WHERE is_open = 0
        ORDER BY close_date
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        logger.info(f"Loaded {len(df)} closed trades from database")
        return df
        
    except Exception as e:
        logger.error(f"Error loading trades from database: {e}")
        raise


def calculate_r_multiples(df: pd.DataFrame, risk_unit_usd: float = 5.0) -> pd.DataFrame:
    """
    Calculate R-multiples for each trade.
    
    Args:
        df: DataFrame with trade data
        risk_unit_usd: Risk unit in USD (default: 5.0)
        
    Returns:
        DataFrame with R-multiples added
    """
    df = df.copy()
    
    # Calculate R-multiple: profit / risk_unit
    df["r_multiple"] = df["close_profit_abs"] / risk_unit_usd
    
    # Calculate cumulative R-multiples
    df["cumulative_r"] = df["r_multiple"].cumsum()
    
    # Calculate running maximum for drawdown calculation
    df["running_max_r"] = df["cumulative_r"].cummax()
    df["drawdown_r"] = df["cumulative_r"] - df["running_max_r"]
    
    # Convert dates to datetime
    df["open_date"] = pd.to_datetime(df["open_date"])
    df["close_date"] = pd.to_datetime(df["close_date"])
    
    # Calculate trade duration in hours
    df["duration_hours"] = (df["close_date"] - df["open_date"]).dt.total_seconds() / 3600
    
    return df


def export_trades(
    db_url: str,
    output_file: str,
    risk_unit_usd: float = 5.0,
) -> None:
    """
    Export trades with R-multiples to CSV.
    
    Args:
        db_url: Database URL
        output_file: Output CSV file path
        risk_unit_usd: Risk unit in USD
    """
    try:
        # Load trades from database
        df = load_trades_from_db(db_url)
        
        if df.empty:
            logger.warning("No closed trades found in database")
            return
            
        # Calculate R-multiples
        df = calculate_r_multiples(df, risk_unit_usd)
        
        # Reorder columns for better readability
        columns = [
            "id", "pair", "strategy", "enter_tag", "exit_reason",
            "open_date", "close_date", "duration_hours",
            "open_rate", "close_rate", "amount", "stake_amount",
            "close_profit", "close_profit_abs", "r_multiple",
            "cumulative_r", "drawdown_r", "fee_open", "fee_close"
        ]
        
        df = df[columns]
        
        # Export to CSV
        df.to_csv(output_file, index=False, float_format="%.4f")
        
        # Print summary statistics
        total_trades = len(df)
        winning_trades = len(df[df["r_multiple"] > 0])
        losing_trades = len(df[df["r_multiple"] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_r = df["r_multiple"].sum()
        max_drawdown_r = df["drawdown_r"].min()
        
        logger.info(f"Trades exported to: {output_file}")
        logger.info(f"Total trades: {total_trades}")
        logger.info(f"Win rate: {win_rate:.2%}")
        logger.info(f"Total return: {total_r:.2f}R")
        logger.info(f"Max drawdown: {max_drawdown_r:.2f}R")
        
        # Export summary statistics
        summary_file = output_file.replace(".csv", "_summary.txt")
        with open(summary_file, "w") as f:
            f.write(f"Trade Summary (Risk Unit: {risk_unit_usd} USD)\n")
            f.write("=" * 50 + "\n")
            f.write(f"Total trades: {total_trades}\n")
            f.write(f"Winning trades: {winning_trades}\n")
            f.write(f"Losing trades: {losing_trades}\n")
            f.write(f"Win rate: {win_rate:.2%}\n")
            f.write(f"Total return: {total_r:.2f}R ({total_r * risk_unit_usd:.2f} USD)\n")
            f.write(f"Max drawdown: {max_drawdown_r:.2f}R ({max_drawdown_r * risk_unit_usd:.2f} USD)\n")
            f.write(f"Average R per trade: {df['r_multiple'].mean():.2f}R\n")
            f.write(f"Best trade: {df['r_multiple'].max():.2f}R\n")
            f.write(f"Worst trade: {df['r_multiple'].min():.2f}R\n")
            
        logger.info(f"Summary saved to: {summary_file}")
        
    except Exception as e:
        logger.error(f"Error exporting trades: {e}")
        raise


def main() -> None:
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description="Export Freqtrade trades with R-multiples")
    
    parser.add_argument(
        "--db-url",
        type=str,
        default="sqlite:///user_data/trades.sqlite",
        help="Database URL (default: sqlite:///user_data/trades.sqlite)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="reports/trades.csv",
        help="Output CSV file (default: reports/trades.csv)"
    )
    
    parser.add_argument(
        "--risk-unit",
        type=float,
        default=5.0,
        help="Risk unit in USD (default: 5.0)"
    )
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Export trades
    export_trades(
        db_url=args.db_url,
        output_file=args.output,
        risk_unit_usd=args.risk_unit,
    )


if __name__ == "__main__":
    main()
