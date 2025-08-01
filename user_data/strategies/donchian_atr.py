"""
DonchianATRTrend Strategy

A robust trend-following breakout strategy using:
- Donchian channels for entry/exit signals
- ATR-based position sizing and stops
- EMA trend filter
- R-based risk management

Author: Senior Quant/DevOps Engineer
Date: 2025-01-25
"""

import logging
import os
from typing import Dict, Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from freqtrade.strategy import IStrategy, merge_informative_pair
from pandas import DataFrame

logger = logging.getLogger(__name__)


class DonchianATRTrend(IStrategy):
    """
    Trend-following breakout strategy using Donchian channels and ATR sizing
    Optimized for 10-minute timeframe with faster signals
    """
    
    # Strategy interface version
    INTERFACE_VERSION = 3
    
    # Optimal timeframe for this strategy
    timeframe = '5m'
    
    # Can this strategy go short?
    can_short = False
    
    # Minimal ROI designed for 5m timeframe
    minimal_roi = {
        "0": 0.04,    # 4% profit target
        "120": 0.02,  # 2% after 10 hours (120 * 5min candles)
        "240": 0.01,  # 1% after 20 hours  
        "360": 0.0    # Break even after 30 hours
    }
    
    # Optimal stoploss designed for the strategy (fallback - we use custom_stoploss)
    stoploss = -0.05
    
    # Trailing stoploss - enabled for 10m timeframe
    trailing_stop = True
    trailing_stop_positive = 0.02  # Start trailing at 2% profit
    trailing_stop_positive_offset = 0.03  # Trail by 3%
    trailing_only_offset_is_reached = True
    
    # Protections optimized for 5m timeframe
    protections = [
        {
            "method": "StoplossGuard",
            "lookback_period_candles": 288,  # 24 hours in 5m candles
            "trade_limit": 4,
            "stop_duration_candles": 72,    # 6 hours
            "only_per_pair": False
        },
        {
            "method": "MaxDrawdown",
            "lookback_period_candles": 2016, # 1 week in 5m candles
            "trade_limit": 4,
            "max_allowed_drawdown": 0.05,
            "stop_duration_candles": 288    # 24 hours
        },
        {
            "method": "CooldownPeriod",
            "stop_duration_candles": 6,     # 30 minutes
            "only_per_pair": True
        }
    ]
    
    # Run "populate_indicators" only for new candle
    process_only_new_candles = True
    
    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 300  # Increased for 10m timeframe
    
    # Strategy parameters optimized for 10m timeframe
    buy_params = {
        "don_len_entry": 18,    # Slightly shorter for faster signals
        "don_len_exit": 9,      # Faster exits
        "ema_len": 200,         # Keep trend filter the same
        "atr_len": 14,          # Standard ATR
        "atr_mult": 1.5,        # Stop distance multiplier
    }
    
    sell_params = {
        "don_len_exit": 10,
    }
    
    # Strategy parameters for hyperopt
    don_len_entry = 20
    don_len_exit = 10
    ema_len = 200  
    atr_len = 14
    atr_mult = 1.5
    
    # Risk management
    r_usd = float(os.getenv('RISK_UNIT_USD', '5.0'))
    max_daily_loss_r = float(os.getenv('MAX_DAILY_LOSS_R', '2.0'))
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators used by the strategy
        """
        
        # Donchian channels
        dataframe['don_upper_entry'] = dataframe['high'].rolling(
            window=self.don_len_entry
        ).max()
        dataframe['don_lower_entry'] = dataframe['low'].rolling(
            window=self.don_len_entry
        ).min()
        
        dataframe['don_upper_exit'] = dataframe['high'].rolling(
            window=self.don_len_exit
        ).max()
        dataframe['don_lower_exit'] = dataframe['low'].rolling(
            window=self.don_len_exit
        ).min()
        dataframe['don_mid_exit'] = (dataframe['don_upper_exit'] + dataframe['don_lower_exit']) / 2
        
        # EMA trend filter
        dataframe['ema'] = ta.EMA(dataframe, timeperiod=self.ema_len)
        
        # ATR for stops and position sizing
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=self.atr_len)
        
        # Additional trend confirmation indicators
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['macd'], dataframe['macdsignal'], dataframe['macdhist'] = ta.MACD(dataframe)
        
        # Volume indicators
        dataframe['volume_sma'] = dataframe['volume'].rolling(window=20).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate buy trend using Donchian breakout + EMA filter
        """
        
        pair = metadata['pair']
        
        # Get latest values for debugging
        if len(dataframe) > 0:
            latest = dataframe.iloc[-1]
            prev = dataframe.iloc[-2] if len(dataframe) > 1 else latest
            
            # Debug logging every few candles - simplified
            if len(dataframe) % 12 == 0:  # Every hour (12 * 5min candles)
                try:
                    price = latest['close'] if pd.notna(latest['close']) else 0
                    ema = latest['ema'] if pd.notna(latest['ema']) else 0
                    logger.info(f"🔍 {pair} Analysis: Price: ${price:.2f} | EMA200: ${ema:.2f}")
                except Exception as e:
                    logger.info(f"🔍 {pair} Analysis error: {e}")
        
        conditions = []
        
        # Primary condition: Close breaks above Donchian upper (entry)
        breakout_condition = dataframe['close'] > dataframe['don_upper_entry'].shift(1)
        conditions.append(breakout_condition)
        
        # Trend filter: Price above EMA
        trend_condition = dataframe['close'] > dataframe['ema']
        conditions.append(trend_condition)
        
        # Volume confirmation: Above average volume
        volume_condition = dataframe['volume'] > dataframe['volume_sma']
        conditions.append(volume_condition)
        
        # RSI not overbought
        rsi_condition = dataframe['rsi'] < 75
        conditions.append(rsi_condition)
        
        # MACD momentum confirmation
        macd_condition = dataframe['macd'] > dataframe['macdsignal']
        conditions.append(macd_condition)
        
        # Check for actual signals
        all_conditions = reduce(lambda x, y: x & y, conditions)
        signal_count = all_conditions.sum()
        
        if signal_count > 0:
            logger.info(f"🎯 BUY SIGNAL for {pair}! Conditions met: {signal_count}")
            logger.info(f"   💰 Price: ${latest['close']:.2f} broke above Donchian: ${prev['don_upper_entry']:.2f}")
        
        if conditions:
            dataframe.loc[all_conditions, 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate sell trend using Donchian mid-line cross
        """
        
        pair = metadata['pair']
        
        conditions = []
        
        # Primary exit: Close drops below Donchian mid (exit)
        mid_exit_condition = dataframe['close'] < dataframe['don_mid_exit']
        conditions.append(mid_exit_condition)
        
        # Alternative exit: RSI overbought
        rsi_exit_condition = dataframe['rsi'] > 80
        conditions.append(rsi_exit_condition)
        
        # Alternative exit: MACD bearish cross
        macd_bear = (
            (dataframe['macd'] < dataframe['macdsignal']) &
            (dataframe['macd'].shift(1) >= dataframe['macdsignal'].shift(1))
        )
        conditions.append(macd_bear)
        
        # Check for exit signals
        any_exit = reduce(lambda x, y: x | y, conditions)
        exit_count = any_exit.sum()
        
        if exit_count > 0:
            latest = dataframe.iloc[-1]
            logger.info(f"🚪 EXIT SIGNAL for {pair}! Exit conditions met: {exit_count}")
            logger.info(f"   💸 Price: ${latest['close']:.2f} | RSI: {latest['rsi']:.1f}")
        
        if conditions:
            dataframe.loc[any_exit, 'exit_long'] = 1
        
        return dataframe
    
    def custom_stake_amount(self, pair: str, current_time, current_rate: float,
                          proposed_stake: float, min_stake: Optional[float], max_stake: float,
                          leverage: float, entry_tag: Optional[str], side: str,
                          **kwargs) -> float:
        """
        Calculate position size based on R (risk unit) and ATR stop distance
        """
        try:
            # Get the latest analyzed dataframe
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            
            if dataframe is None or len(dataframe) == 0:
                logger.warning(f"No dataframe available for {pair}")
                return proposed_stake
            
            # Get latest ATR
            latest_atr = dataframe['atr'].iloc[-1]
            
            if pd.isna(latest_atr) or latest_atr <= 0:
                logger.warning(f"Invalid ATR for {pair}: {latest_atr}")
                return proposed_stake
            
            # Calculate stop distance in USD
            stop_distance = latest_atr * self.atr_mult
            
            # Calculate position size: R / stop_distance
            # This gives us the USD amount to risk per R unit
            calculated_stake = self.r_usd / stop_distance
            
            # Ensure we don't exceed wallet limits
            if calculated_stake > max_stake:
                logger.info(f"Calculated stake {calculated_stake} exceeds max {max_stake} for {pair}")
                return max_stake
            
            if min_stake and calculated_stake < min_stake:
                logger.info(f"Calculated stake {calculated_stake} below min {min_stake} for {pair}")
                return min_stake
            
            logger.info(f"Position sizing for {pair}: ATR={latest_atr:.6f}, "
                       f"Stop distance={stop_distance:.6f}, Stake=${calculated_stake:.2f}")
            
            return calculated_stake
            
        except Exception as e:
            logger.error(f"Error in custom_stake_amount for {pair}: {e}")
            return proposed_stake
    
    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float,
                       current_profit: float, **kwargs) -> float:
        """
        Dynamic stoploss based on ATR
        """
        try:
            # Get the latest analyzed dataframe
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            
            if dataframe is None or len(dataframe) == 0:
                return self.stoploss
            
            # Get latest ATR
            latest_atr = dataframe['atr'].iloc[-1]
            
            if pd.isna(latest_atr) or latest_atr <= 0:
                return self.stoploss
            
            # Calculate ATR-based stop level
            entry_rate = trade.open_rate
            atr_stop_distance = latest_atr * self.atr_mult
            atr_stop_level = entry_rate - atr_stop_distance
            
            # Convert to percentage loss from current rate
            stop_loss_ratio = (atr_stop_level - current_rate) / current_rate
            
            # Ensure stop loss doesn't exceed our maximum
            stop_loss_ratio = max(stop_loss_ratio, -0.10)  # Max 10% loss
            
            return stop_loss_ratio
            
        except Exception as e:
            logger.error(f"Error in custom_stoploss for {pair}: {e}")
            return self.stoploss
    
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                          rate: float, time_in_force: str, current_time,
                          entry_tag: Optional[str], side: str, **kwargs) -> bool:
        """
        Confirm trade entry with additional risk checks
        """
        try:
            # Check daily loss limit
            if hasattr(self, 'daily_loss_r'):
                if self.daily_loss_r >= self.max_daily_loss_r:
                    logger.warning(f"Daily loss limit reached: {self.daily_loss_r}R")
                    return False
            
            # Get current market conditions
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            
            if dataframe is None or len(dataframe) == 0:
                return False
            
            # Additional confirmation: ensure ATR is reasonable
            latest_atr = dataframe['atr'].iloc[-1]
            if pd.isna(latest_atr) or latest_atr <= 0:
                logger.warning(f"Invalid ATR for entry confirmation: {latest_atr}")
                return False
            
            # Check volatility isn't too extreme
            atr_pct = (latest_atr / rate) * 100
            if atr_pct > 5.0:  # 5% ATR might be too volatile
                logger.warning(f"High volatility detected for {pair}: {atr_pct:.2f}%")
                # Still allow but log warning
            
            return True
            
        except Exception as e:
            logger.error(f"Error in confirm_trade_entry for {pair}: {e}")
            return False
    
    # Hyperopt methods
    def hyperopt_parameters(self, space) -> Dict:
        """
        Define hyperopt parameter spaces
        """
        from skopt.space import Integer, Real
        
        return {
            'don_len_entry': Integer(15, 30, name='don_len_entry'),
            'don_len_exit': Integer(5, 15, name='don_len_exit'), 
            'ema_len': Integer(100, 300, name='ema_len'),
            'atr_mult': Real(1.0, 3.0, name='atr_mult'),
        }
    
    def leverage(self, pair: str, current_time, current_rate: float,
                proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                side: str, **kwargs) -> float:
        """
        No leverage for this strategy
        """
        return 1.0


def reduce(function, iterable, initializer=None):
    """
    Reduce function for older Python versions compatibility
    """
    it = iter(iterable)
    if initializer is None:
        value = next(it)
    else:
        value = initializer
    for element in it:
        value = function(value, element)
    return value
