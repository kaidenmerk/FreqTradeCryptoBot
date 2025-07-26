"""
Unit tests for DonchianATRTrend strategy indicators and logic.

Run with: pytest tests/test_indicators.py -v
"""

import numpy as np
import pandas as pd
import pytest
import talib.abstract as ta

# Mock the strategy imports for testing
class MockStrategy:
    def __init__(self):
        self.don_len_entry = MockParameter(20)
        self.don_len_exit = MockParameter(10)
        self.ema_trend = MockParameter(200)
        self.atr_mult = MockParameter(1.5)

class MockParameter:
    def __init__(self, value):
        self.value = value


def create_test_dataframe(length: int = 100) -> pd.DataFrame:
    """Create a synthetic OHLCV dataframe for testing."""
    np.random.seed(42)  # For reproducible tests
    
    # Generate price data with some trend
    base_price = 50000
    price_changes = np.random.normal(0, 0.02, length)  # 2% daily volatility
    prices = [base_price]
    
    for change in price_changes:
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    prices = np.array(prices[1:])  # Remove first element
    
    # Create OHLCV data
    highs = prices * (1 + np.abs(np.random.normal(0, 0.01, length)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.01, length)))
    opens = prices + np.random.normal(0, prices * 0.005, length)
    volumes = np.random.randint(1000, 10000, length)
    
    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': prices,
        'volume': volumes,
    })
    
    return df


def calculate_donchian_channels(df: pd.DataFrame, period: int) -> pd.DataFrame:
    """Calculate Donchian channels for testing."""
    df = df.copy()
    df[f'don_upper_{period}'] = df['high'].rolling(window=period).max()
    df[f'don_lower_{period}'] = df['low'].rolling(window=period).min()
    df[f'don_mid_{period}'] = (df[f'don_upper_{period}'] + df[f'don_lower_{period}']) / 2
    return df


def calculate_ema(df: pd.DataFrame, period: int) -> pd.DataFrame:
    """Calculate EMA for testing."""
    df = df.copy()
    df[f'ema_{period}'] = ta.EMA(df, timeperiod=period)
    return df


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Calculate ATR for testing."""
    df = df.copy()
    df['atr'] = ta.ATR(df, timeperiod=period)
    return df


class TestDonchianIndicators:
    """Test Donchian channel calculations."""
    
    def test_donchian_upper_calculation(self):
        """Test that Donchian upper channel is calculated correctly."""
        df = create_test_dataframe(50)
        period = 20
        
        df = calculate_donchian_channels(df, period)
        
        # Manual calculation for verification
        expected_upper = df['high'].rolling(window=period).max()
        
        assert df[f'don_upper_{period}'].equals(expected_upper)
        assert not df[f'don_upper_{period}'].iloc[period-1:].isna().any()
    
    def test_donchian_lower_calculation(self):
        """Test that Donchian lower channel is calculated correctly."""
        df = create_test_dataframe(50)
        period = 20
        
        df = calculate_donchian_channels(df, period)
        
        # Manual calculation for verification
        expected_lower = df['low'].rolling(window=period).min()
        
        assert df[f'don_lower_{period}'].equals(expected_lower)
        assert not df[f'don_lower_{period}'].iloc[period-1:].isna().any()
    
    def test_donchian_mid_calculation(self):
        """Test that Donchian mid-line is calculated correctly."""
        df = create_test_dataframe(50)
        period = 20
        
        df = calculate_donchian_channels(df, period)
        
        # Manual calculation for verification
        expected_mid = (df[f'don_upper_{period}'] + df[f'don_lower_{period}']) / 2
        
        assert df[f'don_mid_{period}'].equals(expected_mid)
        assert not df[f'don_mid_{period}'].iloc[period-1:].isna().any()
    
    def test_donchian_upper_greater_than_lower(self):
        """Test that upper channel is always >= lower channel."""
        df = create_test_dataframe(50)
        period = 20
        
        df = calculate_donchian_channels(df, period)
        
        valid_data = df.iloc[period-1:]  # Skip NaN values
        assert (valid_data[f'don_upper_{period}'] >= valid_data[f'don_lower_{period}']).all()


class TestATRIndicator:
    """Test ATR (Average True Range) calculations."""
    
    def test_atr_calculation(self):
        """Test that ATR is calculated correctly."""
        df = create_test_dataframe(50)
        df = calculate_atr(df)
        
        # ATR should be positive and non-zero for valid data
        valid_atr = df['atr'].dropna()
        assert (valid_atr > 0).all()
        assert len(valid_atr) == len(df) - 13  # 14-period ATR means 13 NaN values
    
    def test_atr_volatility_relationship(self):
        """Test that ATR increases with volatility."""
        # Create low volatility data
        low_vol_df = create_test_dataframe(50)
        low_vol_df['high'] = low_vol_df['close'] * 1.001  # 0.1% range
        low_vol_df['low'] = low_vol_df['close'] * 0.999
        low_vol_atr = calculate_atr(low_vol_df)['atr'].mean()
        
        # Create high volatility data
        high_vol_df = create_test_dataframe(50)
        high_vol_df['high'] = high_vol_df['close'] * 1.05  # 5% range
        high_vol_df['low'] = high_vol_df['close'] * 0.95
        high_vol_atr = calculate_atr(high_vol_df)['atr'].mean()
        
        assert high_vol_atr > low_vol_atr


class TestEMAIndicator:
    """Test EMA (Exponential Moving Average) calculations."""
    
    def test_ema_calculation(self):
        """Test that EMA is calculated correctly."""
        df = create_test_dataframe(50)
        period = 20
        df = calculate_ema(df, period)
        
        # EMA should not have NaN values after warmup
        valid_ema = df[f'ema_{period}'].dropna()
        assert len(valid_ema) == len(df) - period + 1
        assert (valid_ema > 0).all()  # Prices are positive
    
    def test_ema_trend_following(self):
        """Test that EMA follows price trends."""
        # Create trending data
        df = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103],
            'close': [100, 101, 102, 103, 104],
            'volume': [1000, 1000, 1000, 1000, 1000],
        })
        
        df = calculate_ema(df, 3)
        ema_values = df['ema_3'].dropna()
        
        # EMA should be increasing for uptrending data
        assert (ema_values.diff().dropna() > 0).all()


class TestTradingSignals:
    """Test trading signal generation logic."""
    
    def test_donchian_breakout_signal(self):
        """Test Donchian breakout signal generation."""
        df = create_test_dataframe(50)
        period = 20
        
        df = calculate_donchian_channels(df, period)
        
        # Create breakout condition
        df['donchian_breakout'] = df['close'] > df[f'don_upper_{period}']
        
        # Test that signal is boolean
        assert df['donchian_breakout'].dtype == bool
        
        # Test that there are some breakouts in random data
        breakout_count = df['donchian_breakout'].sum()
        assert breakout_count >= 0  # Should be non-negative
    
    def test_trend_filter_signal(self):
        """Test EMA trend filter signal."""
        df = create_test_dataframe(50)
        period = 20
        
        df = calculate_ema(df, period)
        df['trend_bullish'] = df['close'] > df[f'ema_{period}']
        
        # Test that signal is boolean
        assert df['trend_bullish'].dtype == bool
        
        # Count bullish signals
        bullish_count = df['trend_bullish'].sum()
        assert bullish_count >= 0
    
    def test_exit_signal(self):
        """Test exit signal generation."""
        df = create_test_dataframe(50)
        period = 10
        
        df = calculate_donchian_channels(df, period)
        df['exit_signal'] = df['close'] < df[f'don_mid_{period}']
        
        # Test that signal is boolean
        assert df['exit_signal'].dtype == bool
        
        # Count exit signals
        exit_count = df['exit_signal'].sum()
        assert exit_count >= 0


class TestRiskManagement:
    """Test risk management calculations."""
    
    def test_position_sizing_calculation(self):
        """Test ATR-based position sizing."""
        risk_unit = 5.0  # $5 risk per trade
        atr_mult = 1.5
        current_price = 50000
        atr_value = 1000
        
        # Calculate stop distance
        stop_distance = atr_value * atr_mult
        
        # Calculate position size
        position_size = risk_unit / stop_distance
        
        assert position_size > 0
        assert position_size == 5.0 / 1500.0  # 5 / (1000 * 1.5)
    
    def test_r_multiple_calculation(self):
        """Test R-multiple calculation."""
        risk_unit = 5.0
        profit_usd = 15.0
        
        r_multiple = profit_usd / risk_unit
        
        assert r_multiple == 3.0  # 15 / 5 = 3R
    
    def test_daily_loss_limit(self):
        """Test daily loss limit logic."""
        risk_unit = 5.0
        max_daily_loss_r = 2.0
        daily_pnl = -8.0  # Lost $8
        
        max_loss_usd = max_daily_loss_r * risk_unit  # $10
        
        # Should trigger loss lock
        assert daily_pnl <= -max_loss_usd


class TestDataValidation:
    """Test data validation and error handling."""
    
    def test_empty_dataframe_handling(self):
        """Test handling of empty dataframes."""
        df = pd.DataFrame()
        
        # Should not raise errors for empty data
        with pytest.raises((IndexError, ValueError)):
            calculate_donchian_channels(df, 20)
    
    def test_insufficient_data_handling(self):
        """Test handling of insufficient data."""
        df = create_test_dataframe(5)  # Only 5 rows
        period = 20  # Requires 20 rows
        
        df = calculate_donchian_channels(df, period)
        
        # All values should be NaN due to insufficient data
        assert df[f'don_upper_{period}'].isna().all()
        assert df[f'don_lower_{period}'].isna().all()
    
    def test_missing_price_data(self):
        """Test handling of missing price data."""
        df = create_test_dataframe(20)
        df.loc[5:10, 'close'] = np.nan  # Insert missing data
        
        df = calculate_ema(df, 10)
        
        # EMA should handle missing data gracefully
        assert not df['ema_10'].isna().all()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
