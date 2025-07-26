"""
DonchianATRTrend Strategy

A professional trend-following strategy based on Donchian channels with ATR-based
risk management. Implements the Turtle trading system with modern enhancements.

Author: Senior Quant Dev
Date: 2025-07-25
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from freqtrade.strategy import (
    BooleanParameter,
    DecimalParameter,
    IntParameter,
    IStrategy,
    informative,
)
from pandas import DataFrame

logger = logging.getLogger(__name__)


class DonchianATRTrend(IStrategy):
    """
    Donchian Channel breakout strategy with ATR-based position sizing and risk management.
    
    Strategy Logic:
    - Entry: Price breaks above Donchian upper band AND close > EMA200
    - Exit: Price closes below Donchian mid or ATR-based stop loss
    - Risk: Fixed R per trade using ATR for position sizing
    """

    # Strategy interface version
    INTERFACE_VERSION = 3

    # Timeframe for the strategy
    timeframe = "1h"

    # Can this strategy go short?
    can_short = False

    # Minimal ROI designed for the strategy (3% target)
    minimal_roi = {"0": 0.03}

    # Optimal stoploss designed for the strategy (will be overridden by custom logic)
    stoploss = -0.10

    # Trailing stop
    trailing_stop = False
    trailing_stop_positive = None
    trailing_stop_positive_offset = 0.0
    trailing_only_offset_is_reached = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 250

    # Hyperopt parameters
    don_len_entry = IntParameter(10, 60, default=20, space="buy", optimize=True)
    don_len_exit = IntParameter(5, 40, default=10, space="sell", optimize=True)
    ema_trend = IntParameter(100, 300, default=200, space="buy", optimize=True)
    atr_mult = DecimalParameter(1.0, 3.0, default=1.5, space="sell", optimize=True)
    
    # Risk management parameters
    enable_daily_loss_lock = BooleanParameter(default=True, space="protection")

    def __init__(self, config: dict) -> None:
        """Initialize the strategy with risk management parameters."""
        super().__init__(config)
        
        # Risk unit from environment or config
        self.risk_unit_usd = float(os.getenv("RISK_UNIT_USD", "5.0"))
        self.max_daily_loss_r = float(os.getenv("MAX_DAILY_LOSS_R", "2.0"))
        
        # Daily P&L tracking
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        
        logger.info(f"Strategy initialized with R={self.risk_unit_usd} USD, "
                   f"Max daily loss={self.max_daily_loss_r}R")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add technical indicators to the given DataFrame.
        
        Args:
            dataframe: Raw OHLCV data
            metadata: Additional information about the pair
            
        Returns:
            DataFrame with technical indicators
        """
        # Donchian Channels for entries
        dataframe["don_upper_entry"] = (
            dataframe["high"].rolling(window=self.don_len_entry.value).max()
        )
        dataframe["don_lower_entry"] = (
            dataframe["low"].rolling(window=self.don_len_entry.value).min()
        )
        dataframe["don_mid_entry"] = (
            dataframe["don_upper_entry"] + dataframe["don_lower_entry"]
        ) / 2

        # Donchian Channels for exits (shorter period)
        dataframe["don_upper_exit"] = (
            dataframe["high"].rolling(window=self.don_len_exit.value).max()
        )
        dataframe["don_lower_exit"] = (
            dataframe["low"].rolling(window=self.don_len_exit.value).min()
        )
        dataframe["don_mid_exit"] = (
            dataframe["don_upper_exit"] + dataframe["don_lower_exit"]
        ) / 2

        # Trend filter - EMA
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=self.ema_trend.value)

        # ATR for volatility-based stops and position sizing
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_stop_dist"] = dataframe["atr"] * self.atr_mult.value

        # Additional indicators for context
        dataframe["volume_sma"] = dataframe["volume"].rolling(window=20).mean()
        
        # Signal flags
        dataframe["donchian_breakout"] = dataframe["close"] > dataframe["don_upper_entry"]
        dataframe["trend_bullish"] = dataframe["close"] > dataframe["ema_trend"]
        dataframe["exit_signal"] = dataframe["close"] < dataframe["don_mid_exit"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate buy signal based on Donchian breakout and trend filter.
        
        Args:
            dataframe: DataFrame with indicators
            metadata: Additional information about the pair
            
        Returns:
            DataFrame with buy signals
        """
        conditions = [
            # Donchian breakout above upper band
            dataframe["donchian_breakout"],
            
            # Trend filter: price above EMA
            dataframe["trend_bullish"],
            
            # Volume confirmation (optional)
            dataframe["volume"] > dataframe["volume_sma"] * 0.8,
            
            # ATR not too small (avoid low volatility periods)
            dataframe["atr"] > dataframe["close"] * 0.005,  # 0.5% minimum ATR
        ]

        dataframe.loc[
            np.logical_and.reduce(conditions) & ~self._is_daily_loss_locked(),
            "enter_long"
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate sell signal based on Donchian mid-line break or stop loss.
        
        Args:
            dataframe: DataFrame with indicators
            metadata: Additional information about the pair
            
        Returns:
            DataFrame with sell signals
        """
        dataframe.loc[
            dataframe["exit_signal"],
            "exit_long"
        ] = 1

        return dataframe

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: Optional[float],
        max_stake: float,
        leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> float:
        """
        Calculate position size based on ATR and fixed risk amount.
        
        Risk per trade = R (fixed USD amount)
        Position size = R / (ATR * multiplier)
        
        Args:
            pair: Trading pair
            current_time: Current timestamp
            current_rate: Current price
            proposed_stake: Freqtrade's proposed stake
            min_stake: Minimum stake allowed
            max_stake: Maximum stake allowed
            leverage: Leverage (if applicable)
            entry_tag: Entry tag
            side: Trade side (buy/sell)
            
        Returns:
            Calculated stake amount
        """
        try:
            # Get the latest dataframe
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            
            if dataframe.empty:
                logger.warning(f"No data available for {pair}, using proposed stake")
                return proposed_stake
                
            # Get latest ATR value
            latest_atr = dataframe["atr"].iloc[-1]
            
            if pd.isna(latest_atr) or latest_atr <= 0:
                logger.warning(f"Invalid ATR for {pair}: {latest_atr}, using proposed stake")
                return proposed_stake
                
            # Calculate stop distance in price units
            stop_distance = latest_atr * self.atr_mult.value
            
            # Calculate position size: R / stop_distance
            calculated_stake = self.risk_unit_usd / stop_distance
            
            # Apply bounds
            if min_stake and calculated_stake < min_stake:
                logger.info(f"Calculated stake {calculated_stake} below minimum {min_stake}")
                return min_stake
                
            if calculated_stake > max_stake:
                logger.info(f"Calculated stake {calculated_stake} above maximum {max_stake}")
                return max_stake
                
            logger.info(f"Position sizing for {pair}: ATR={latest_atr:.4f}, "
                       f"Stop distance={stop_distance:.4f}, Stake={calculated_stake:.2f}")
                       
            return calculated_stake
            
        except Exception as e:
            logger.error(f"Error calculating stake for {pair}: {e}")
            return proposed_stake

    def custom_stoploss(
        self,
        pair: str,
        trade: object,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs
    ) -> float:
        """
        Custom stoploss based on ATR distance.
        
        Args:
            pair: Trading pair
            trade: Trade object
            current_time: Current timestamp
            current_rate: Current price
            current_profit: Current profit percentage
            
        Returns:
            Stoploss value (negative percentage)
        """
        try:
            # Get the latest dataframe
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            
            if dataframe.empty:
                return self.stoploss
                
            # Get latest ATR
            latest_atr = dataframe["atr"].iloc[-1]
            
            if pd.isna(latest_atr) or latest_atr <= 0:
                return self.stoploss
                
            # Calculate stop distance
            stop_distance = latest_atr * self.atr_mult.value
            
            # Convert to percentage
            stop_percentage = -(stop_distance / trade.open_rate)
            
            # Ensure it's not too tight or too wide
            stop_percentage = max(stop_percentage, -0.15)  # Max 15% stop
            stop_percentage = min(stop_percentage, -0.01)  # Min 1% stop
            
            return stop_percentage
            
        except Exception as e:
            logger.error(f"Error calculating custom stoploss for {pair}: {e}")
            return self.stoploss

    def _is_daily_loss_locked(self) -> bool:
        """
        Check if daily loss limit has been reached.
        
        Returns:
            True if trading should be locked due to daily losses
        """
        if not self.enable_daily_loss_lock.value:
            return False
            
        # Reset daily P&L if it's a new day
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
            logger.info("Daily P&L reset for new trading day")
            
        # Check if loss limit exceeded
        max_loss_usd = self.max_daily_loss_r * self.risk_unit_usd
        
        if self.daily_pnl <= -max_loss_usd:
            logger.warning(f"Daily loss limit reached: {self.daily_pnl:.2f} USD "
                          f"(limit: -{max_loss_usd:.2f} USD). Trading locked until tomorrow.")
            return True
            
        return False

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> bool:
        """
        Confirm trade entry based on additional checks.
        
        Args:
            pair: Trading pair
            order_type: Order type
            amount: Order amount
            rate: Order rate
            time_in_force: Time in force
            current_time: Current timestamp
            entry_tag: Entry tag
            side: Trade side
            
        Returns:
            True if trade should be entered
        """
        # Check daily loss lock
        if self._is_daily_loss_locked():
            logger.info(f"Trade entry rejected for {pair}: daily loss limit reached")
            return False
            
        # Additional entry confirmations can be added here
        # e.g., market hours, volatility checks, correlation limits
        
        return True

    def confirm_trade_exit(
        self,
        pair: str,
        trade: object,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        exit_reason: str,
        current_time: datetime,
        **kwargs
    ) -> bool:
        """
        Confirm trade exit and update daily P&L tracking.
        
        Args:
            pair: Trading pair
            trade: Trade object
            order_type: Order type
            amount: Order amount
            rate: Order rate
            time_in_force: Time in force
            exit_reason: Reason for exit
            current_time: Current timestamp
            
        Returns:
            True if trade should be exited
        """
        # Calculate trade P&L in USD
        if hasattr(trade, 'calc_profit_ratio'):
            profit_ratio = trade.calc_profit_ratio(rate)
            profit_usd = profit_ratio * trade.stake_amount
            
            # Update daily P&L
            self.daily_pnl += profit_usd
            
            # Calculate R-multiple
            r_multiple = profit_usd / self.risk_unit_usd
            
            logger.info(f"Trade exit confirmed for {pair}: "
                       f"P&L={profit_usd:.2f} USD ({r_multiple:.2f}R), "
                       f"Daily P&L={self.daily_pnl:.2f} USD, "
                       f"Reason={exit_reason}")
        
        return True
