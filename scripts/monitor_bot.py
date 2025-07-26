#!/usr/bin/env python3
"""
Bot monitoring and health check script.

Usage:
    python scripts/monitor_bot.py --config config.live.json
"""

import argparse
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FreqtradeMonitor:
    """Monitor Freqtrade bot health and performance."""
    
    def __init__(self, config_file: str):
        """Initialize monitor with config file."""
        self.config_file = config_file
        self.config = self._load_config()
        self.api_url = self._get_api_url()
        
    def _load_config(self) -> Dict:
        """Load Freqtrade configuration."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise
            
    def _get_api_url(self) -> Optional[str]:
        """Get API server URL from config."""
        api_config = self.config.get('api_server', {})
        if not api_config.get('enabled', False):
            logger.warning("API server not enabled in config")
            return None
            
        host = api_config.get('listen_ip_address', '127.0.0.1')
        port = api_config.get('listen_port', 8080)
        return f"http://{host}:{port}"
        
    def check_bot_status(self) -> Dict:
        """Check if bot is running and healthy."""
        if not self.api_url:
            return {"status": "unknown", "error": "API not configured"}
            
        try:
            response = requests.get(f"{self.api_url}/api/v1/status", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
            
    def get_open_trades(self) -> Dict:
        """Get current open trades."""
        if not self.api_url:
            return {"trades": [], "error": "API not configured"}
            
        try:
            response = requests.get(f"{self.api_url}/api/v1/status", timeout=10)
            response.raise_for_status()
            data = response.json()
            return {"trades": data.get("open_trades", []), "trade_count": len(data.get("open_trades", []))}
        except Exception as e:
            return {"trades": [], "error": str(e)}
            
    def get_performance_stats(self) -> Dict:
        """Get performance statistics from database."""
        db_url = self.config.get('db_url', 'sqlite:///user_data/trades.sqlite')
        
        if not db_url.startswith('sqlite:///'):
            return {"error": "Only SQLite databases supported"}
            
        db_path = db_url.replace('sqlite:///', '')
        
        if not os.path.exists(db_path):
            return {"error": f"Database file not found: {db_path}"}
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get recent performance (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            # Total trades
            cursor.execute("SELECT COUNT(*) FROM trades WHERE is_open = 0")
            total_trades = cursor.fetchone()[0]
            
            # Recent trades
            cursor.execute(
                "SELECT COUNT(*) FROM trades WHERE is_open = 0 AND close_date > ?",
                (thirty_days_ago.isoformat(),)
            )
            recent_trades = cursor.fetchone()[0]
            
            # Win rate
            cursor.execute(
                "SELECT COUNT(*) FROM trades WHERE is_open = 0 AND close_profit > 0 AND close_date > ?",
                (thirty_days_ago.isoformat(),)
            )
            recent_wins = cursor.fetchone()[0]
            
            # Total profit
            cursor.execute(
                "SELECT SUM(close_profit_abs) FROM trades WHERE is_open = 0 AND close_date > ?",
                (thirty_days_ago.isoformat(),)
            )
            recent_profit = cursor.fetchone()[0] or 0
            
            conn.close()
            
            win_rate = (recent_wins / recent_trades * 100) if recent_trades > 0 else 0
            
            return {
                "total_trades": total_trades,
                "recent_trades_30d": recent_trades,
                "win_rate_30d": round(win_rate, 1),
                "profit_30d": round(recent_profit, 2),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": str(e)}
            
    def check_daily_limits(self) -> Dict:
        """Check if daily loss limits are being respected."""
        # This would integrate with the strategy's daily loss tracking
        # For now, return placeholder
        return {
            "daily_pnl": 0.0,
            "daily_limit": -10.0,  # 2R * 5 USD
            "limit_hit": False,
            "trades_today": 0
        }
        
    def send_alert(self, message: str, level: str = "INFO") -> None:
        """Send alert notification (placeholder for Discord/Telegram)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{level}] {timestamp}: {message}")
        
        # TODO: Implement Discord/Telegram notifications
        
    def run_health_check(self) -> Dict:
        """Run comprehensive health check."""
        logger.info("Running bot health check...")
        
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "bot_status": self.check_bot_status(),
            "open_trades": self.get_open_trades(),
            "performance": self.get_performance_stats(),
            "daily_limits": self.check_daily_limits(),
        }
        
        # Check for issues
        issues = []
        
        if health_report["bot_status"].get("status") != "running":
            issues.append("Bot is not running")
            
        if "error" in health_report["open_trades"]:
            issues.append(f"API error: {health_report['open_trades']['error']}")
            
        trade_count = health_report["open_trades"].get("trade_count", 0)
        max_trades = self.config.get("max_open_trades", 2)
        
        if trade_count >= max_trades:
            issues.append(f"Maximum trades reached: {trade_count}/{max_trades}")
            
        if health_report["daily_limits"].get("limit_hit"):
            issues.append("Daily loss limit hit - trading locked")
            
        health_report["issues"] = issues
        health_report["healthy"] = len(issues) == 0
        
        # Send alerts for issues
        if issues:
            for issue in issues:
                self.send_alert(issue, "WARNING")
        else:
            logger.info("✅ Bot health check passed - all systems normal")
            
        return health_report
        

def main():
    """Main monitoring function."""
    parser = argparse.ArgumentParser(description="Freqtrade bot monitor")
    
    parser.add_argument(
        "--config",
        type=str,
        default="config.live.json",
        help="Config file path"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=300,  # 5 minutes
        help="Check interval in seconds"
    )
    
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously"
    )
    
    args = parser.parse_args()
    
    monitor = FreqtradeMonitor(args.config)
    
    if args.continuous:
        logger.info(f"Starting continuous monitoring (interval: {args.interval}s)")
        
        while True:
            try:
                health_report = monitor.run_health_check()
                
                if not health_report["healthy"]:
                    logger.warning(f"Health check failed: {health_report['issues']}")
                    
                time.sleep(args.interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    else:
        # Single health check
        health_report = monitor.run_health_check()
        print(json.dumps(health_report, indent=2))


if __name__ == "__main__":
    main()
