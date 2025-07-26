#!/usr/bin/env python3
"""
Download historical data for Freqtrade strategies.

Usage:
    python scripts/download_data.py --exchange coinbasepro --pairs BTC/USD ETH/USD --timeframe 1h --days 365
"""

import argparse
import logging
import subprocess
import sys
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_data(
    exchange: str,
    pairs: List[str],
    timeframe: str = "1h",
    days: int = 365,
    config: Optional[str] = None,
) -> bool:
    """
    Download historical data using freqtrade download-data command.
    
    Args:
        exchange: Exchange name (e.g., 'coinbasepro', 'binance')
        pairs: List of trading pairs (e.g., ['BTC/USD', 'ETH/USD'])
        timeframe: Timeframe for data (e.g., '1h', '4h', '1d')
        days: Number of days to download
        config: Optional config file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Build the freqtrade command
        cmd = [
            "freqtrade", "download-data",
            "--exchange", exchange,
            "--timeframe", timeframe,
            "--days", str(days),
        ]
        
        # Add config if specified
        if config:
            cmd.extend(["--config", config])
        
        # Add pairs
        for pair in pairs:
            cmd.extend(["--pairs", pair])
            
        logger.info(f"Downloading data: {' '.join(cmd)}")
        
        # Execute the command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Data download completed successfully")
            logger.info(result.stdout)
            return True
        else:
            logger.error(f"Data download failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error downloading data: {e}")
        return False


def main() -> None:
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description="Download historical data for Freqtrade")
    
    parser.add_argument(
        "--exchange", 
        type=str, 
        default="alpaca",
        help="Exchange name (default: alpaca, options: alpaca, coinbase)"
    )
    
    parser.add_argument(
        "--pairs", 
        nargs="+", 
        default=["AAPL/USD", "TSLA/USD", "SPY/USD"],
        help="Trading pairs to download (default: AAPL/USD TSLA/USD SPY/USD)"
    )
    
    parser.add_argument(
        "--timeframe", 
        type=str, 
        default="1h",
        help="Timeframe for data (default: 1h)"
    )
    
    parser.add_argument(
        "--days", 
        type=int, 
        default=365,
        help="Number of days to download (default: 365)"
    )
    
    parser.add_argument(
        "--config", 
        type=str,
        help="Config file path (optional)"
    )
    
    args = parser.parse_args()
    
    # Download the data
    success = download_data(
        exchange=args.exchange,
        pairs=args.pairs,
        timeframe=args.timeframe,
        days=args.days,
        config=args.config,
    )
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
