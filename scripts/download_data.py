#!/usr/bin/env python3
"""
Data Download Script for Freqtrade

Downloads historical OHLCV data for specified pairs and timeframes.
Supports multiple exchanges and flexible date ranges.

Usage:
    python scripts/download_data.py --exchange coinbase --days 365
    python scripts/download_data.py --exchange coinbase --timeframe 1h --pairs BTC/USD ETH/USD
"""

import argparse
import logging
import subprocess
import sys
from typing import List

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_data(
    exchange: str = "coinbase",
    quote_currency: str = "USD", 
    timeframe: str = "1h",
    days: str = "365",
    pairs: List[str] = None,
    config: str = "user_data/config.paper.json"
) -> bool:
    """
    Download historical data using Freqtrade's download-data command.
    
    Args:
        exchange: Exchange name (coinbase, binance, etc.)
        quote_currency: Quote currency (USD, USDT, etc.)
        timeframe: Timeframe (1m, 5m, 1h, 1d, etc.)
        days: Number of days to download
        pairs: Specific pairs to download (optional)
        config: Config file path
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Build the command
        cmd = [
            "freqtrade", "download-data",
            "--exchange", exchange,
            "--timeframe", timeframe,
            "--days", days,
            "--config", config
        ]
        
        # Add quote currency if no specific pairs provided
        if not pairs:
            cmd.extend(["--quote-currency", quote_currency])
        else:
            # Add specific pairs
            for pair in pairs:
                cmd.extend(["--pairs", pair])
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        # Run the command
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        logger.info("Data download completed successfully!")
        logger.info(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error downloading data: {e}")
        logger.error(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


def main():
    """Main function to handle command line arguments and execute download."""
    parser = argparse.ArgumentParser(
        description="Download historical data for Freqtrade",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--exchange", 
        default="coinbase",
        help="Exchange to download from"
    )
    
    parser.add_argument(
        "--quote", "--quote-currency",
        default="USD",
        help="Quote currency to filter pairs"
    )
    
    parser.add_argument(
        "--timeframe", 
        default="1h",
        choices=["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"],
        help="Timeframe for the data"
    )
    
    parser.add_argument(
        "--days",
        default="365", 
        help="Number of days to download"
    )
    
    parser.add_argument(
        "--pairs",
        nargs="+",
        help="Specific pairs to download (e.g., BTC/USD ETH/USD)"
    )
    
    parser.add_argument(
        "--config",
        default="user_data/config.paper.json",
        help="Config file to use"
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
    
    # Download data
    success = download_data(
        exchange=args.exchange,
        quote_currency=args.quote,
        timeframe=args.timeframe,
        days=args.days,
        pairs=args.pairs,
        config=args.config
    )
    
    if not success:
        sys.exit(1)
    
    logger.info("Data download script completed successfully!")


if __name__ == "__main__":
    main()
