# Freqtrade Crypto Trading Bot

A professional cryptocurrency trading bot built with Freqtrade, featuring the **DonchianATRTrend** strategy - a robust trend-following system based on Donchian channels with ATR-based risk management.

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Copy environment template and fill in your API keys
cp .env.example .env
# Edit .env with your exchange API credentials

# Install dependencies (auto-detects Poetry or falls back to pip)
make setup

# Download historical data
make data

# Run backtest
make backtest

# Start paper trading
make trade-paper
```

### 2. API Key Setup (.env file)
```bash
# Coinbase Pro API credentials
CB_KEY=your_coinbase_pro_api_key_here
CB_SECRET=your_coinbase_pro_api_secret_here
CB_PASSPHRASE=your_coinbase_pro_passphrase_here

# Risk management
RISK_UNIT_USD=5.0
MAX_DAILY_LOSS_R=2.0
```

## 📊 Strategy: DonchianATRTrend

### Core Logic
- **Trend Following**: Donchian channel breakouts with EMA trend filter
- **Risk Management**: ATR-based position sizing and stop losses
- **Risk Unit**: Fixed $5 risk per trade (configurable)
- **Daily Loss Lock**: Trading stops after losing 2R in a day

### Entry Conditions
- Price breaks above 20-period Donchian upper band
- Price is above 200-period EMA (trend filter)
- Volume confirmation
- Minimum volatility threshold (0.5% ATR)

### Exit Conditions
- Price closes below Donchian mid-line (10-period)
- ATR-based stop loss (1.5x ATR distance)
- 3% ROI target (fallback)

### Position Sizing
```
Position Size = Risk Unit / (ATR × Multiplier)
Example: $5 / (1000 × 1.5) = $0.0033 per unit
```

### Hyperopt Parameters
- `don_len_entry`: Entry Donchian period (10-60, default 20)
- `don_len_exit`: Exit Donchian period (5-40, default 10)
- `ema_trend`: EMA trend filter period (100-300, default 200)
- `atr_mult`: ATR stop multiplier (1.0-3.0, default 1.5)

## 🛠️ Available Commands

### Core Operations
```bash
make setup          # Install dependencies
make data           # Download historical data
make backtest       # Run strategy backtest
make hyperopt       # Optimize parameters
make trade-paper    # Start paper trading
make trade-live     # Start live trading (careful!)
make export         # Export trades with R-multiples
make mc             # Run Monte Carlo analysis
make test           # Run unit tests
```

### Analysis & Monitoring
```bash
make plot-dataframe # Plot strategy indicators
make plot-profit    # Plot P&L charts
make show-trades    # Show trade analysis
make logs           # Monitor live logs
```

## 📁 Project Structure

```
freqtrade-crypto-1.0/
├── user_data/
│   ├── strategies/
│   │   └── donchian_atr.py      # Main strategy
│   ├── logs/                    # Bot logs
│   └── data/                    # Historical data
├── scripts/
│   ├── download_data.py         # Data download utility
│   ├── export_trades.py         # Trade export with R-multiples
│   └── mc_bootstrap.py          # Monte Carlo analysis
├── tests/
│   └── test_indicators.py       # Unit tests
├── reports/                     # Analysis outputs
├── config.paper.json           # Paper trading config
├── config.live.json            # Live trading config
├── .env.example                 # Environment template
├── pyproject.toml              # Poetry dependencies
├── requirements.txt            # Pip dependencies
├── Makefile                    # Automation commands
└── README.md                   # This file
```

## 💰 Risk Management

### Risk Unit System
- **R**: Fixed risk amount per trade ($5 default)
- **Position sizing**: Calculated using ATR volatility
- **R-multiples**: Track performance (1R = $5 profit/loss)

### Daily Loss Protection
- Trading stops after losing 2R in a single day
- Resets automatically at start of new trading day
- Configurable via `MAX_DAILY_LOSS_R` environment variable

### Monte Carlo Analysis
```bash
# Export trades and run Monte Carlo simulation
make mc

# Generates:
# - reports/monte_carlo_analysis.png
# - reports/monte_carlo_stats.txt
# - reports/monte_carlo_results.csv
```

## 📈 Usage Examples

### Backtesting Different Timeframes
```bash
# 4-hour timeframe
freqtrade backtesting --config config.paper.json --strategy DonchianATRTrend --timeframe 4h

# Daily timeframe
freqtrade backtesting --config config.paper.json --strategy DonchianATRTrend --timeframe 1d
```

### Custom Pair Lists
Edit `config.paper.json` or `config.live.json`:
```json
"pair_whitelist": [
    "BTC/USD",
    "ETH/USD",
    "ADA/USD",
    "DOT/USD",
    "LINK/USD"
]
```

### Hyperparameter Optimization
```bash
# Optimize buy/sell parameters
make hyperopt

# Custom optimization
freqtrade hyperopt \
    --config config.paper.json \
    --strategy DonchianATRTrend \
    --spaces buy sell \
    --epochs 500 \
    --timerange 20230101-20240101
```

## 🔧 Advanced Configuration

### Exchange Setup
Currently configured for Coinbase Pro. To use other exchanges:

1. Update configs (`config.paper.json`, `config.live.json`)
2. Change exchange name and API key variables
3. Update pair format (e.g., `BTC/USDT` for Binance)

### Custom Risk Settings
```bash
# Change risk unit
export RISK_UNIT_USD=10.0

# Change daily loss limit
export MAX_DAILY_LOSS_R=3.0
```

### Telegram Notifications
Add to `.env`:
```bash
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

Enable in config files:
```json
"telegram": {
    "enabled": true,
    "token": "${TELEGRAM_TOKEN}",
    "chat_id": "${TELEGRAM_CHAT_ID}"
}
```

## 🧪 Testing

### Unit Tests
```bash
# Run all tests
make test

# Run specific test categories
python -m pytest tests/test_indicators.py::TestDonchianIndicators -v
python -m pytest tests/test_indicators.py::TestRiskManagement -v
```

### Strategy Validation
```bash
# Validate strategy syntax
freqtrade test-pairlist --config config.paper.json --strategy DonchianATRTrend

# Dry run validation
freqtrade trade --config config.paper.json --strategy DonchianATRTrend --dry-run
```

## 📊 Performance Analysis

### Trade Export & Analysis
```bash
# Export trades with R-multiples
make export

# Analyze results
python scripts/export_trades.py --help
python scripts/mc_bootstrap.py --help
```

### Key Metrics
- **Win Rate**: Percentage of profitable trades
- **R-Expectancy**: Average R-multiple per trade
- **Max Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted returns

## 🚀 Going Live

### Pre-Flight Checklist
1. ✅ Successful paper trading for at least 2 weeks
2. ✅ Monte Carlo analysis shows acceptable risk
3. ✅ API keys configured and tested
4. ✅ Stake amounts set appropriately in `config.live.json`
5. ✅ Monitoring and alerts configured

### Live Trading
```bash
# Start live trading (will prompt for confirmation)
make trade-live

# Monitor in real-time
make logs
```

## 🔒 Security Best Practices

- Use API keys with minimal permissions (trade only, no withdrawals)
- Enable IP whitelisting on exchange
- Start with small stake amounts
- Monitor positions regularly
- Keep bot updated

## 🛟 Troubleshooting

### Common Issues

**TA-Lib Installation (Windows)**
```bash
# Download wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
pip install TA_Lib-0.4.28-cp311-cp311-win_amd64.whl
```

**TA-Lib Installation (Linux)**
```bash
sudo apt-get install ta-lib-dev
pip install ta-lib
```

**Data Download Issues**
```bash
# Verify exchange connection
freqtrade test-pairlist --config config.paper.json

# Manual data download
freqtrade download-data --exchange coinbasepro --pairs BTC/USD --timeframe 1h --days 30
```

**Strategy Errors**
```bash
# Check strategy syntax
python -c "from user_data.strategies.donchian_atr import DonchianATRTrend; print('Strategy OK')"

# Validate indicators
freqtrade backtesting --config config.paper.json --strategy DonchianATRTrend --timerange 20241201-20241202
```

## 📚 Additional Resources

- [Freqtrade Documentation](https://www.freqtrade.io/)
- [Coinbase Pro API](https://docs.pro.coinbase.com/)
- [TA-Lib Indicators](https://ta-lib.org/function.html)
- [Risk Management Guide](https://www.freqtrade.io/en/stable/strategy-customization/#custom-stoploss)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## ⚠️ Disclaimer

**This software is for educational purposes only. Trading cryptocurrencies involves substantial risk of loss and is not suitable for every investor. Past performance does not guarantee future results. Only trade with money you can afford to lose.**

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Ready to deploy?** Run through the checklist:

1. `cp .env.example .env && fill keys`
2. `make setup`
3. `make data` 
4. `make backtest`
5. `make trade-paper`
6. Watch logs, then flip to live config

Need Discord/Telegram notifications or VPS deployment help? Let me know! 🚀
