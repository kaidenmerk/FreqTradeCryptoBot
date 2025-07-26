"""
Unit tests for Freqtrade DonchianATRTrend strategy

Tests indicator calculations, entry/exit signals, and strategy logic.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

# Import the strategy
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "user_data" / "strategies"))

from donchian_atr import DonchianATRTrend


class TestDonchianATRTrend:
    """Test cases for DonchianATRTrend strategy"""
    
    @pytest.fixture
    def strategy(self):
        """Create strategy instance for testing"""
        return DonchianATRTrend()
    
    @pytest.fixture
    def sample_dataframe(self):
        """Create sample OHLCV dataframe for testing"""
        np.random.seed(42)  # For reproducible tests
        
        dates = pd.date_range('2023-01-01', periods=300, freq='1H')
        
        # Create realistic OHLCV data with some trends
        base_price = 50000
        returns = np.random.normal(0, 0.02, len(dates))  # 2% volatility
        
        # Add some trend
        trend = np.linspace(0, 0.1, len(dates))
        returns += trend / len(dates)
        
        prices = base_price * np.cumprod(1 + returns)
        
        # Generate OHLC from prices
        high = prices * (1 + np.abs(np.random.normal(0, 0.005, len(dates))))
        low = prices * (1 - np.abs(np.random.normal(0, 0.005, len(dates))))
        open_prices = prices + np.random.normal(0, prices * 0.001)
        close_prices = prices
        
        volume = np.random.uniform(100, 1000, len(dates))
        
        df = pd.DataFrame({
            'date': dates,
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close_prices,
            'volume': volume
        })
        
        return df
    
    def test_strategy_initialization(self, strategy):
        """Test strategy initializes correctly"""
        assert strategy.timeframe == '1h'
        assert strategy.can_short is False
        assert strategy.startup_candle_count == 250
        assert hasattr(strategy, 'don_len_entry')
        assert hasattr(strategy, 'don_len_exit')
        assert hasattr(strategy, 'ema_len')
        assert hasattr(strategy, 'atr_len')
        assert hasattr(strategy, 'atr_mult')
    
    def test_populate_indicators(self, strategy, sample_dataframe):
        """Test that indicators are calculated correctly"""
        df = strategy.populate_indicators(sample_dataframe, {'pair': 'BTC/USD'})
        
        # Check that all required indicators are present
        required_indicators = [
            'don_upper_entry', 'don_lower_entry',
            'don_upper_exit', 'don_lower_exit', 'don_mid_exit',
            'ema', 'atr', 'rsi', 'macd', 'macdsignal', 'macdhist',
            'volume_sma'
        ]
        
        for indicator in required_indicators:
            assert indicator in df.columns, f"Missing indicator: {indicator}"
        
        # Check indicator values are reasonable
        assert not df['atr'].isnull().all(), "ATR should not be all null"
        assert not df['ema'].isnull().all(), "EMA should not be all null"
        assert not df['rsi'].isnull().all(), "RSI should not be all null"
        
        # Check Donchian channels are calculated correctly
        # Upper channel should be >= high prices
        valid_upper = df['don_upper_entry'].dropna()
        valid_high = df['high'][df['don_upper_entry'].notna()]
        assert (valid_upper >= valid_high).all(), "Donchian upper should be >= high"
        
        # Lower channel should be <= low prices  
        valid_lower = df['don_lower_entry'].dropna()
        valid_low = df['low'][df['don_lower_entry'].notna()]
        assert (valid_lower <= valid_low).all(), "Donchian lower should be <= low"
        
        # Mid line should be between upper and lower
        valid_indices = ~(df['don_upper_exit'].isnull() | df['don_lower_exit'].isnull())
        upper_exit = df.loc[valid_indices, 'don_upper_exit']
        lower_exit = df.loc[valid_indices, 'don_lower_exit']  
        mid_exit = df.loc[valid_indices, 'don_mid_exit']
        
        assert ((mid_exit >= lower_exit) & (mid_exit <= upper_exit)).all(), \
            "Donchian mid should be between upper and lower"
    
    def test_populate_entry_trend(self, strategy, sample_dataframe):
        """Test entry signal generation"""
        # First populate indicators
        df = strategy.populate_indicators(sample_dataframe, {'pair': 'BTC/USD'})
        
        # Then populate entry signals
        df = strategy.populate_entry_trend(df, {'pair': 'BTC/USD'})
        
        # Check that enter_long column exists
        assert 'enter_long' in df.columns
        
        # Check that signals are binary (0 or 1)
        entry_values = df['enter_long'].dropna().unique()
        assert all(val in [0, 1] for val in entry_values), "Entry signals should be 0 or 1"
        
        # Check that we have some entry signals (not all zeros)
        assert df['enter_long'].sum() > 0, "Should have at least some entry signals"
        
        # Verify entry logic: entry signals should occur when close > don_upper_entry
        entry_signals = df[df['enter_long'] == 1]
        if len(entry_signals) > 0:
            # Note: We shift don_upper_entry by 1 in the strategy
            prev_upper = df['don_upper_entry'].shift(1)
            entry_closes = entry_signals['close']
            entry_indices = entry_signals.index
            prev_upper_at_entry = prev_upper.loc[entry_indices]
            
            # Should be mostly true (allowing for some noise due to other conditions)
            breakout_condition = entry_closes > prev_upper_at_entry
            assert breakout_condition.sum() / len(breakout_condition) > 0.8, \
                "Most entry signals should occur on Donchian breakouts"
    
    def test_populate_exit_trend(self, strategy, sample_dataframe):
        """Test exit signal generation"""
        # Populate indicators and entry signals first
        df = strategy.populate_indicators(sample_dataframe, {'pair': 'BTC/USD'})
        df = strategy.populate_entry_trend(df, {'pair': 'BTC/USD'})
        
        # Then populate exit signals
        df = strategy.populate_exit_trend(df, {'pair': 'BTC/USD'})
        
        # Check that exit_long column exists
        assert 'exit_long' in df.columns
        
        # Check that signals are binary (0 or 1)
        exit_values = df['exit_long'].dropna().unique()
        assert all(val in [0, 1] for val in exit_values), "Exit signals should be 0 or 1"
    
    @patch('user_data.strategies.donchian_atr.logger')
    def test_custom_stake_amount(self, mock_logger, strategy):
        """Test custom stake amount calculation"""
        # Mock the dataframe provider
        mock_dp = MagicMock()
        strategy.dp = mock_dp
        
        # Create sample dataframe with ATR
        df = pd.DataFrame({
            'atr': [0.02, 0.025, 0.03]  # 2-3% ATR
        })
        
        mock_dp.get_analyzed_dataframe.return_value = (df, None)
        
        # Test calculation
        stake = strategy.custom_stake_amount(
            pair='BTC/USD',
            current_time=datetime.now(timezone.utc),
            current_rate=50000,
            proposed_stake=100,
            min_stake=10,
            max_stake=1000,
            leverage=1.0,
            entry_tag=None,
            side='long'
        )
        
        # Should calculate based on R / (ATR * atr_mult)
        expected_stake = strategy.r_usd / (0.03 * strategy.atr_mult)  # Using last ATR
        
        assert isinstance(stake, float)
        assert stake > 0
        assert abs(stake - expected_stake) < 0.01, f"Expected {expected_stake}, got {stake}"
    
    def test_custom_stake_amount_edge_cases(self, strategy):
        """Test custom stake amount with edge cases"""
        # Mock dataframe provider
        mock_dp = MagicMock()
        strategy.dp = mock_dp
        
        # Test with no dataframe
        mock_dp.get_analyzed_dataframe.return_value = (None, None)
        
        stake = strategy.custom_stake_amount(
            pair='BTC/USD',
            current_time=datetime.now(timezone.utc),
            current_rate=50000,
            proposed_stake=100,
            min_stake=10,
            max_stake=1000,
            leverage=1.0,
            entry_tag=None,
            side='long'
        )
        
        # Should return proposed stake when no data available
        assert stake == 100
        
        # Test with invalid ATR
        df = pd.DataFrame({'atr': [np.nan, 0, -0.01]})
        mock_dp.get_analyzed_dataframe.return_value = (df, None)
        
        stake = strategy.custom_stake_amount(
            pair='BTC/USD',
            current_time=datetime.now(timezone.utc),
            current_rate=50000,
            proposed_stake=100,
            min_stake=10,
            max_stake=1000,
            leverage=1.0,
            entry_tag=None,
            side='long'
        )
        
        # Should return proposed stake when ATR is invalid
        assert stake == 100
    
    def test_custom_stoploss(self, strategy):
        """Test custom stoploss calculation"""
        # Mock dataframe provider
        mock_dp = MagicMock()
        strategy.dp = mock_dp
        
        # Sample dataframe with ATR
        df = pd.DataFrame({
            'atr': [0.02, 0.025, 0.03]
        })
        
        mock_dp.get_analyzed_dataframe.return_value = (df, None)
        
        # Mock trade object
        mock_trade = MagicMock()
        mock_trade.open_rate = 50000
        
        current_rate = 51000  # 2% profit
        
        stoploss_ratio = strategy.custom_stoploss(
            pair='BTC/USD',
            trade=mock_trade,
            current_time=datetime.now(timezone.utc),
            current_rate=current_rate,
            current_profit=0.02
        )
        
        # Should be negative (loss ratio)
        assert stoploss_ratio < 0
        
        # Should be reasonable (not more than 10% loss)
        assert stoploss_ratio >= -0.10
        
        # Calculate expected stop level
        atr_stop_distance = 0.03 * strategy.atr_mult  # Using last ATR
        expected_stop_level = mock_trade.open_rate - atr_stop_distance
        expected_ratio = (expected_stop_level - current_rate) / current_rate
        expected_ratio = max(expected_ratio, -0.10)  # Capped at -10%
        
        assert abs(stoploss_ratio - expected_ratio) < 0.001
    
    def test_confirm_trade_entry(self, strategy):
        """Test trade entry confirmation"""
        # Mock dataframe provider
        mock_dp = MagicMock()
        strategy.dp = mock_dp
        
        # Valid dataframe with good ATR
        df = pd.DataFrame({
            'atr': [0.02, 0.025, 0.03]
        })
        
        mock_dp.get_analyzed_dataframe.return_value = (df, None)
        
        # Should confirm entry with valid conditions
        confirmed = strategy.confirm_trade_entry(
            pair='BTC/USD',
            order_type='limit',
            amount=0.001,
            rate=50000,
            time_in_force='GTC',
            current_time=datetime.now(timezone.utc),
            entry_tag=None,
            side='long'
        )
        
        assert confirmed is True
        
        # Test with extreme volatility
        df_volatile = pd.DataFrame({
            'atr': [3000, 3500, 4000]  # Very high ATR (8% of price)
        })
        
        mock_dp.get_analyzed_dataframe.return_value = (df_volatile, None)
        
        # Should still confirm but log warning
        confirmed = strategy.confirm_trade_entry(
            pair='BTC/USD',
            order_type='limit',
            amount=0.001,
            rate=50000,
            time_in_force='GTC',
            current_time=datetime.now(timezone.utc),
            entry_tag=None,
            side='long'
        )
        
        assert confirmed is True  # Still allows trade but logs warning
    
    def test_leverage(self, strategy):
        """Test leverage method returns 1.0 (no leverage)"""
        leverage = strategy.leverage(
            pair='BTC/USD',
            current_time=datetime.now(timezone.utc),
            current_rate=50000,
            proposed_leverage=2.0,
            max_leverage=5.0,
            entry_tag=None,
            side='long'
        )
        
        assert leverage == 1.0
    
    def test_hyperopt_parameters(self, strategy):
        """Test hyperopt parameters definition"""
        from unittest.mock import Mock
        
        # Mock the space module
        mock_space = Mock()
        mock_space.Integer = Mock(return_value='integer_space')
        mock_space.Real = Mock(return_value='real_space')
        
        params = strategy.hyperopt_parameters(mock_space)
        
        # Check that all expected parameters are defined
        expected_params = ['don_len_entry', 'don_len_exit', 'ema_len', 'atr_mult']
        for param in expected_params:
            assert param in params
        
        # Check that Integer and Real were called appropriately
        assert mock_space.Integer.call_count >= 3  # At least 3 integer parameters
        assert mock_space.Real.call_count >= 1     # At least 1 real parameter


# Integration tests
class TestStrategyIntegration:
    """Integration tests with more realistic scenarios"""
    
    @pytest.fixture
    def strategy(self):
        return DonchianATRTrend()
    
    def test_full_indicator_pipeline(self, strategy):
        """Test the full indicator calculation pipeline"""
        # Create a longer, more realistic dataset
        np.random.seed(123)
        dates = pd.date_range('2023-01-01', periods=1000, freq='1H')
        
        # Create trending market data
        base_price = 45000
        trend = np.linspace(0, 0.3, len(dates))  # 30% uptrend over period
        noise = np.random.normal(0, 0.015, len(dates))  # 1.5% noise
        
        returns = trend/len(dates) + noise
        prices = base_price * np.cumprod(1 + returns)
        
        # Generate realistic OHLCV
        high = prices * (1 + np.abs(np.random.normal(0, 0.003, len(dates))))
        low = prices * (1 - np.abs(np.random.normal(0, 0.003, len(dates))))
        open_prices = np.roll(prices, 1)  # Previous close as open
        open_prices[0] = prices[0]
        
        volume = np.random.lognormal(5, 1, len(dates))  # Log-normal volume
        
        df = pd.DataFrame({
            'date': dates,
            'open': open_prices,
            'high': high,
            'low': low,
            'close': prices,
            'volume': volume
        })
        
        # Run full pipeline
        df = strategy.populate_indicators(df, {'pair': 'BTC/USD'})
        df = strategy.populate_entry_trend(df, {'pair': 'BTC/USD'})
        df = strategy.populate_exit_trend(df, {'pair': 'BTC/USD'})
        
        # Validate results
        assert len(df) == 1000
        assert df['enter_long'].sum() > 0, "Should generate some entry signals"
        assert df['exit_long'].sum() > 0, "Should generate some exit signals"
        
        # Check signal quality
        entry_signals = df[df['enter_long'] == 1]
        if len(entry_signals) > 5:  # If we have enough signals
            # Entry signals should generally occur during uptrends
            entry_prices = entry_signals['close']
            price_changes = entry_prices.pct_change(20).dropna()  # 20-period change
            uptrend_entries = (price_changes > 0).sum()
            
            # At least 60% of entries should be in uptrending periods
            assert uptrend_entries / len(price_changes) > 0.6, \
                "Most entries should occur during uptrends"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
