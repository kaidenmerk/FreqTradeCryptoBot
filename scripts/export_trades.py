#!/usr/bin/env python3
"""
Trade Export Script for Freqtrade

Exports trades from the SQLite database to CSV format with additional analytics
including R-multiples, win rates, and performance metrics.

Usage:
    python scripts/export_trades.py --config user_data/config.paper.json
    python scripts/export_trades.py --output reports/trades_analysis.csv
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_freqtrade_config(config_path: str) -> Dict:
    """Load Freqtrade configuration from JSON file."""
    import json
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        raise


def connect_to_database(db_url: str):
    """Connect to the Freqtrade database."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        return session, engine
    except Exception as e:
        logger.error(f"Error connecting to database {db_url}: {e}")
        raise


def export_trades_from_db(config_path: str) -> pd.DataFrame:
    """
    Export trades directly from Freqtrade database.
    
    Args:
        config_path: Path to Freqtrade config file
        
    Returns:
        DataFrame with trade data
    """
    try:
        # Load config
        config = load_freqtrade_config(config_path)
        db_url = config.get('db_url', 'sqlite:///user_data/trades.sqlite')
        
        logger.info(f"Connecting to database: {db_url}")
        
        # Connect to database
        session, engine = connect_to_database(db_url)
        
        # Query trades table
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
            amount_requested,
            stake_amount,
            close_profit,
            close_profit_abs,
            sell_reason as exit_reason,
            strategy,
            enter_tag,
            timeframe,
            open_date,
            close_date,
            open_order_id,
            stop_loss,
            initial_stop_loss,
            stoploss_order_id,
            stoploss_last_update,
            max_rate,
            min_rate,
            exit_order_id,
            realized_profit
        FROM trades
        ORDER BY open_date DESC
        """
        
        df = pd.read_sql_query(query, engine)
        logger.info(f"Exported {len(df)} trades from database")
        
        # Close connections
        session.close()
        engine.dispose()
        
        return df
        
    except Exception as e:
        logger.error(f"Error exporting trades: {e}")
        raise


def calculate_r_multiples(df: pd.DataFrame, r_usd: float = 5.0) -> pd.DataFrame:
    """
    Calculate R-multiples for each trade.
    
    R-multiple = (Exit Price - Entry Price) / (Entry Price - Stop Loss)
    
    Args:
        df: DataFrame with trade data
        r_usd: Risk amount in USD per trade
        
    Returns:
        DataFrame with R-multiple calculations
    """
    try:
        df = df.copy()
        
        # Calculate trade duration
        df['open_date'] = pd.to_datetime(df['open_date'])
        df['close_date'] = pd.to_datetime(df['close_date'])
        df['duration_hours'] = (df['close_date'] - df['open_date']).dt.total_seconds() / 3600
        
        # Calculate R-multiples for closed trades
        closed_trades = df[df['is_open'] == 0].copy()
        
        if len(closed_trades) > 0:
            # Simple R calculation based on profit/loss vs risk amount
            closed_trades['r_multiple'] = closed_trades['close_profit_abs'] / r_usd
            
            # Alternative R calculation using stop loss (if available)
            mask = (closed_trades['initial_stop_loss'].notna()) & (closed_trades['initial_stop_loss'] > 0)
            if mask.any():
                entry_stop_diff = closed_trades.loc[mask, 'open_rate'] - closed_trades.loc[mask, 'initial_stop_loss']
                profit_loss = closed_trades.loc[mask, 'close_rate'] - closed_trades.loc[mask, 'open_rate']
                closed_trades.loc[mask, 'r_multiple_stop'] = profit_loss / entry_stop_diff
            
            # Merge back
            df = df.merge(
                closed_trades[['id', 'r_multiple', 'duration_hours']].fillna(0),
                on='id',
                how='left'
            )
            
            if 'r_multiple_stop' in closed_trades.columns:
                df = df.merge(
                    closed_trades[['id', 'r_multiple_stop']].fillna(0),
                    on='id',
                    how='left'
                )
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculating R-multiples: {e}")
        return df


def calculate_performance_metrics(df: pd.DataFrame) -> Dict:
    """Calculate performance metrics from trades."""
    try:
        closed_trades = df[df['is_open'] == 0]
        
        if len(closed_trades) == 0:
            return {"error": "No closed trades found"}
        
        metrics = {}
        
        # Basic metrics
        metrics['total_trades'] = len(closed_trades)
        metrics['winning_trades'] = len(closed_trades[closed_trades['close_profit'] > 0])
        metrics['losing_trades'] = len(closed_trades[closed_trades['close_profit'] <= 0])
        metrics['win_rate'] = (metrics['winning_trades'] / metrics['total_trades']) * 100
        
        # Profit metrics
        metrics['total_profit_abs'] = closed_trades['close_profit_abs'].sum()
        metrics['total_profit_pct'] = closed_trades['close_profit'].sum() * 100
        
        metrics['avg_profit_abs'] = closed_trades['close_profit_abs'].mean()
        metrics['avg_profit_pct'] = closed_trades['close_profit'].mean() * 100
        
        metrics['best_trade_abs'] = closed_trades['close_profit_abs'].max()
        metrics['worst_trade_abs'] = closed_trades['close_profit_abs'].min()
        
        metrics['best_trade_pct'] = closed_trades['close_profit'].max() * 100
        metrics['worst_trade_pct'] = closed_trades['close_profit'].min() * 100
        
        # R-multiple metrics (if available)
        if 'r_multiple' in closed_trades.columns:
            r_data = closed_trades['r_multiple'].dropna()
            if len(r_data) > 0:
                metrics['avg_r_multiple'] = r_data.mean()
                metrics['total_r_multiple'] = r_data.sum()
                metrics['best_r_multiple'] = r_data.max()
                metrics['worst_r_multiple'] = r_data.min()
        
        # Duration metrics
        if 'duration_hours' in closed_trades.columns:
            duration_data = closed_trades['duration_hours'].dropna()
            if len(duration_data) > 0:
                metrics['avg_duration_hours'] = duration_data.mean()
                metrics['median_duration_hours'] = duration_data.median()
        
        # Drawdown calculation (simple)
        closed_trades_sorted = closed_trades.sort_values('close_date')
        cumulative_profit = closed_trades_sorted['close_profit_abs'].cumsum()
        running_max = cumulative_profit.expanding().max()
        drawdown = (cumulative_profit - running_max)
        metrics['max_drawdown_abs'] = drawdown.min()
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {e}")
        return {"error": str(e)}


def main():
    """Main function to handle command line arguments and execute export."""
    parser = argparse.ArgumentParser(
        description="Export Freqtrade trades with analytics",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--config",
        default="user_data/config.paper.json",
        help="Freqtrade config file path"
    )
    
    parser.add_argument(
        "--output",
        default="reports/trades_export.csv",
        help="Output CSV file path"
    )
    
    parser.add_argument(
        "--r-usd",
        type=float,
        default=5.0,
        help="Risk amount in USD per trade for R-multiple calculation"
    )
    
    parser.add_argument(
        "--metrics-only",
        action="store_true",
        help="Only show performance metrics, don't export CSV"
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
        # Export trades
        logger.info(f"Exporting trades from config: {args.config}")
        df = export_trades_from_db(args.config)
        
        if len(df) == 0:
            logger.warning("No trades found in database")
            return
        
        # Calculate R-multiples
        logger.info("Calculating R-multiples...")
        df = calculate_r_multiples(df, args.r_usd)
        
        # Calculate performance metrics
        logger.info("Calculating performance metrics...")
        metrics = calculate_performance_metrics(df)
        
        # Print metrics
        logger.info("\n" + "="*50)
        logger.info("PERFORMANCE METRICS")
        logger.info("="*50)
        
        for key, value in metrics.items():
            if isinstance(value, float):
                if 'pct' in key or 'rate' in key:
                    logger.info(f"{key.replace('_', ' ').title()}: {value:.2f}%")
                elif 'r_multiple' in key:
                    logger.info(f"{key.replace('_', ' ').title()}: {value:.2f}R")
                else:
                    logger.info(f"{key.replace('_', ' ').title()}: {value:.2f}")
            else:
                logger.info(f"{key.replace('_', ' ').title()}: {value}")
        
        if not args.metrics_only:
            # Create output directory
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Export to CSV
            df.to_csv(args.output, index=False)
            logger.info(f"Trades exported to: {args.output}")
            
            # Also export metrics to JSON
            metrics_path = output_path.parent / f"{output_path.stem}_metrics.json"
            import json
            with open(metrics_path, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)
            logger.info(f"Metrics exported to: {metrics_path}")
        
        logger.info("Trade export completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
