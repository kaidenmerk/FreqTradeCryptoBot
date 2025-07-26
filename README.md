# Freqtrade Crypto Bot - DonchianATRTrend Strategy

A professional-grade cryptocurrency trading bot using Freqtrade with a robust trend-following breakout strategy. Features Donchian channel breakouts, ATR-based position sizing, comprehensive risk management, and Monte Carlo analysis tools.

## 🚀 Quick Start

```bash
# 1. Copy environment template and add your API keys
cp .env.example .env
# Edit .env with your Coinbase API credentials

# 2. Install dependencies
make setup

# 3. Download historical data
make data

# 4. Run backtest
make backtest

# 5. Start paper trading
make trade-paper
```

## 📋 Prerequisites

### Required Software
- **Python 3.11+** - [Download Python](https://www.python.org/downloads/)
- **TA-Lib** - Technical analysis library

### TA-Lib Installation

**Windows:**
```bash
# Option 1: Binary wheel (recommended)
pip install TA-Lib-bin

# Option 2: From Christoph Gohlke's wheels
# Download appropriate .whl from https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
pip install TA_Lib-0.4.25-cp311-cp311-win_amd64.whl
```

**Linux/macOS:**
```bash
# Install system dependencies first
sudo apt-get install build-essential  # Ubuntu/Debian
brew install ta-lib                    # macOS

# Then install Python package
pip install TA-Lib
```

### API Setup

1. **Coinbase Advanced** (recommended for lower fees):
   - Create account at [Coinbase Advanced](https://advanced-trade.coinbase.com/)
   - Generate API key with trading permissions
   - Note: Different from regular Coinbase Pro

2. **Alternative Exchanges:**
   - Binance, Kraken, etc. supported via CCXT
   - Update exchange config in JSON files

## 🏗️ Project Structure

```
freqtrade-crypto-1.0/
├── user_data/
│   ├── strategies/
│   │   └── donchian_atr.py      # Main trading strategy
│   ├── config.paper.json        # Paper trading config
│   ├── config.live.json         # Live trading config
│   └── protections.json         # Risk protection rules
├── scripts/
│   ├── download_data.py         # Data download utility
│   ├── export_trades.py         # Trade analysis & export
│   └── mc_bootstrap.py          # Monte Carlo simulation
├── tests/
│   └── test_indicators.py       # Unit tests
├── reports/                     # Generated analysis files
├── .env.example                 # Environment template
├── requirements.txt             # Python dependencies
├── Makefile                     # Common commands
└── README.md                    # This file
```

## 📊 Strategy Overview

### DonchianATRTrend Strategy

**Core Logic:**
- **Entry**: Price breaks above Donchian upper channel (20-period) + trending above EMA(200)
- **Exit**: Price drops below Donchian mid-line (10-period) OR RSI overbought OR MACD bearish cross
- **Stop Loss**: Dynamic ATR-based stops (1.5x ATR distance)
- **Position Sizing**: R-based sizing where R = $5 risk per trade

**Technical Indicators:**
- Donchian Channels (20 entry, 10 exit)
- EMA(200) trend filter
- ATR(14) for volatility measurement
- RSI(14) momentum
- MACD trend confirmation
- Volume confirmation

**Risk Management:**
- Maximum 2 open positions
- R-multiple based position sizing
- ATR trailing stops
- Multiple protection layers (StoplossGuard, MaxDrawdown, CooldownPeriod)
- Daily loss limits

## 🛠️ Configuration

### Environment Variables (.env)

```bash
# Coinbase API (required)
CB_KEY=your_api_key_here
CB_SECRET=your_secret_here
CB_PASSPHRASE=your_passphrase_here

# Risk Management
RISK_UNIT_USD=5.0              # Risk per trade in USD
MAX_DAILY_LOSS_R=2.0           # Max daily loss in R units
```

### Trading Pairs

Default pairs (configurable in config files):
- BTC/USD
- ETH/USD  
- SOL/USD
- MATIC/USD
- AVAX/USD

### Key Parameters

**Strategy Parameters:**
- `don_len_entry`: 20 (Donchian breakout period)
- `don_len_exit`: 10 (Donchian exit period)
- `ema_len`: 200 (Trend filter period)
- `atr_mult`: 1.5 (Stop loss multiplier)

**Risk Parameters:**
- `r_usd`: $5 (Risk unit per trade)
- `max_open_trades`: 2
- `stake_amount`: "unlimited" (paper) / $25 (live)

## ⚡ Commands Reference

### Setup & Installation
```bash
make setup          # Install dependencies
make clean          # Clean temporary files
```

### Data Management
```bash
make data           # Download 365 days of data
make data-week      # Download 1 week (testing)
make data-custom DAYS=30 PAIRS="BTC/USD ETH/USD"  # Custom download
```

### Testing & Validation
```bash
make test           # Run unit tests
make backtest       # Full backtest
make backtest-fast  # Quick 30-day backtest
make validate       # Validate configuration
```

### Hyperoptimization
```bash
make hyperopt       # Full hyperopt (500 epochs)
make hyperopt-quick # Quick hyperopt (100 epochs)
make hyperopt-show  # Show results
```

### Trading
```bash
make trade-paper    # Start paper trading
make trade-live     # Start live trading (careful!)
make stop           # Stop all bots
make status         # Check bot status
make balance        # Check account balance
```

### Analysis & Reporting
```bash
make export         # Export trades to CSV
make mc             # Monte Carlo analysis
make plot-results   # Generate performance plots
make logs           # Show recent logs
```

## 📈 Analysis Tools

### 1. Trade Export & Analytics
```bash
python scripts/export_trades.py --config user_data/config.paper.json
```

**Features:**
- R-multiple calculations
- Win rate and profit metrics
- Drawdown analysis
- Duration statistics
- Performance metrics export

### 2. Monte Carlo Bootstrap
```bash
python scripts/mc_bootstrap.py --trades reports/trades_export.csv --simulations 5000
```

**Output:**
- Expected return distributions
- Maximum drawdown probabilities
- Value at Risk (VaR) calculations
- Risk metrics visualization
- Equity curve projections

**Key Metrics:**
- Probability of drawdown > 3R, 5R, 10R
- Expected shortfall (tail risk)
- Distribution of returns
- 95% confidence intervals

### 3. Performance Visualization
- Equity curve plots
- Drawdown histograms  
- Risk/return scatter plots
- Monthly/weekly breakdowns

## ⚠️ Risk Management

### Built-in Protections

1. **StoplossGuard**: Stops trading after 2 stop losses in 24 candles
2. **MaxDrawdown**: Stops at 5% drawdown over 168 candles (1 week)
3. **CooldownPeriod**: 6-candle cooldown between trades per pair
4. **Position Limits**: Maximum 2 open positions

### R-Based Position Sizing

Position size calculated as:
```
Stake Amount = R_USD / (ATR × ATR_Multiplier × Current_Price)
```

Example: With R=$5, ATR=0.02, multiplier=1.5:
- Stop distance = 0.02 × 1.5 = 0.03 (3%)
- Position size = $5 / 0.03 = $166.67

### Daily Loss Limits

Bot automatically stops trading if daily losses exceed configured R limits.

## 🔧 Customization

### Modifying Strategy Parameters

Edit `user_data/strategies/donchian_atr.py`:

```python
# Strategy parameters
don_len_entry = 25      # Longer breakout period
don_len_exit = 8        # Shorter exit period  
ema_len = 150          # Faster trend filter
atr_mult = 2.0         # Wider stops
r_usd = 10.0           # Higher risk per trade
```

### Adding New Pairs

Edit config files to add pairs:
```json
{
  "exchange": {
    "pair_whitelist": [
      "BTC/USD",
      "ETH/USD", 
      "ADA/USD",    // Add new pairs here
      "DOT/USD"
    ]
  }
}
```

### Hyperopt Optimization

Strategy supports hyperoptimization of key parameters:
- Donchian periods (entry/exit)
- EMA trend filter length
- ATR stop multiplier

## 📊 Web Interface

Paper trading includes web interface at `http://localhost:8080`:
- **Username**: freqtrade
- **Password**: freqtrade

**Features:**
- Real-time trade monitoring
- Performance charts
- Balance tracking
- Manual trade controls
- Strategy metrics

## 🐛 Troubleshooting

### Common Issues

**1. TA-Lib Installation Errors**
```bash
# Windows: Use binary wheel
pip uninstall TA-Lib
pip install TA-Lib-bin

# Linux: Install system dependencies
sudo apt-get update
sudo apt-get install build-essential
```

**2. API Connection Issues**
- Verify API keys in `.env` file
- Check API permissions (trading enabled)
- Ensure IP whitelist (if configured)
- Test with paper trading first

**3. No Entry Signals**
```bash
# Check if data is available
make data

# Validate strategy
make validate

# Run quick backtest
make backtest-fast
```

**4. High Memory Usage**
- Reduce data range for backtesting
- Use fewer pairs for testing
- Clear cache: `make clean`

### Debug Mode

Enable verbose logging:
```bash
# In config files, set:
"verbosity": 3

# Or use freqtrade directly:
freqtrade trade --config user_data/config.paper.json --verbose
```

### Log Files

Check logs in:
- `user_data/logs/freqtrade.log`
- Recent logs: `make logs`

## 🔒 Security Best Practices

1. **API Keys**:
   - Use API keys with minimal required permissions
   - Restrict IP access if possible
   - Never commit API keys to version control

2. **Live Trading**:
   - Start with small amounts
   - Test thoroughly in paper mode
   - Monitor closely initially
   - Set up alerts/notifications

3. **Risk Limits**:
   - Never risk more than you can afford to lose
   - Set strict daily/weekly loss limits
   - Use position sizing appropriately

## 📧 Notifications (Optional)

### Telegram Integration
```bash
# Add to .env:
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Add to config:
"telegram": {
  "enabled": true,
  "token": "${TELEGRAM_TOKEN}",
  "chat_id": "${TELEGRAM_CHAT_ID}"
}
```

### Discord Webhooks
```bash
# Add to .env:
DISCORD_WEBHOOK_URL=your_webhook_url

# Add to config:
"discord": {
  "enabled": true,
  "webhook_url": "${DISCORD_WEBHOOK_URL}"
}
```

## 🚀 Deployment

### VPS Deployment

1. **Server Setup**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip build-essential
```

2. **Process Management**:
```bash
# Using screen
screen -S freqtrade
make trade-live
# Ctrl+A, D to detach

# Using systemd (recommended)
sudo cp freqtrade.service /etc/systemd/system/
sudo systemctl enable freqtrade
sudo systemctl start freqtrade
```

3. **Monitoring**:
```bash
# Check status
sudo systemctl status freqtrade

# View logs
journalctl -u freqtrade -f
```

## 📚 Further Learning

### Freqtrade Documentation
- [Official Docs](https://www.freqtrade.io/)
- [Strategy Development](https://www.freqtrade.io/en/stable/strategy-customization/)
- [Hyperopt Guide](https://www.freqtrade.io/en/stable/hyperopt/)

### Trading Strategy Resources
- [Donchian Channels](https://www.investopedia.com/terms/d/donchian-channels.asp)
- [ATR Position Sizing](https://www.investopedia.com/articles/trading/08/average-true-range.asp)
- [Risk Management](https://www.investopedia.com/articles/trading/09/risk-management.asp)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/improvement`
3. Make changes and test: `make test`
4. Commit changes: `git commit -am 'Add improvement'`
5. Push branch: `git push origin feature/improvement`
6. Submit pull request

## ⚖️ License

This project is for educational purposes. Use at your own risk. No warranty provided.

**Disclaimer**: Cryptocurrency trading involves substantial risk. Past performance does not guarantee future results. Only trade with funds you can afford to lose.

---

## 🏁 RUN CHECKLIST

1. ✅ `cp .env.example .env` - Fill in your API keys
2. ✅ `make setup` - Install dependencies  
3. ✅ `make data` - Download historical data
4. ✅ `make backtest` - Run initial backtest
5. ✅ `make trade-paper` - Start paper trading
6. ✅ Watch trades in dry-run mode
7. ✅ Optional: `make hyperopt` - Optimize parameters
8. ✅ When confident: Switch to `config.live.json` with small capital

**🎯 Next Steps**: Ask me about Discord/Telegram notifications or VPS deployment when ready!

---

*Happy Trading! 📈*
