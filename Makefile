# Freqtrade Crypto Bot Makefile
# 
# Common commands for development, testing, and trading

.PHONY: help setup data clean test backtest hyperopt trade-paper trade-live export mc plot-results stop logs

# Default target
help:
	@echo "Freqtrade Crypto Bot - Available Commands:"
	@echo ""
	@echo "  Setup & Installation:"
	@echo "    make setup          Install dependencies and setup environment"
	@echo "    make clean          Clean cache and temporary files"
	@echo ""
	@echo "  Data Management:"
	@echo "    make data           Download default historical data (365 days)"
	@echo "    make data-week      Download 1 week of data (faster for testing)"
	@echo "    make data-custom DAYS=30 PAIRS='BTC/USD ETH/USD'  Download custom data"
	@echo ""
	@echo "  Testing & Validation:"
	@echo "    make test           Run unit tests"
	@echo "    make backtest       Run backtest with default settings"
	@echo "    make backtest-fast  Quick backtest (30 days, fewer pairs)"
	@echo "    make hyperopt       Run hyperoptimization"
	@echo "    make hyperopt-quick Quick hyperopt (100 epochs)"
	@echo ""
	@echo "  Trading:"
	@echo "    make trade-paper    Start paper trading"
	@echo "    make trade-live     Start live trading (BE CAREFUL!)"
	@echo "    make stop           Stop all running bots"
	@echo ""
	@echo "  Analysis & Reporting:"
	@echo "    make export         Export trades to CSV with analytics"
	@echo "    make mc             Run Monte Carlo bootstrap analysis"
	@echo "    make plot-results   Generate strategy performance plots"
	@echo "    make logs           Show recent trading logs"
	@echo ""
	@echo "  Utilities:"
	@echo "    make status         Show bot status and open trades"
	@echo "    make balance        Show account balance"
	@echo "    make validate       Validate strategy and configuration"

# Variables
PYTHON := python
STRATEGY := DonchianATRTrend
CONFIG_PAPER := user_data/config.paper.json
CONFIG_LIVE := user_data/config.live.json
DAYS := 365
PAIRS := BTC/USD ETH/USD SOL/USD MATIC/USD AVAX/USD

# Setup and installation
setup:
	@echo "Installing Python dependencies..."
	$(PYTHON) -m pip install --upgrade pip
	pip install -r requirements.txt
	@echo ""
	@echo "Creating .env file from template..."
	@if not exist .env (copy .env.example .env) else (echo .env already exists)
	@echo ""
	@echo "Setup complete! Please edit .env file with your API keys."
	@echo "Then run 'make data' to download historical data."

# Data management
data:
	@echo "Downloading historical data ($(DAYS) days)..."
	$(PYTHON) scripts/download_data.py --days $(DAYS) --config $(CONFIG_PAPER)

data-week:
	@echo "Downloading 1 week of data for quick testing..."
	$(PYTHON) scripts/download_data.py --days 7 --config $(CONFIG_PAPER)

data-custom:
	@echo "Downloading custom data: $(DAYS) days for pairs: $(PAIRS)"
	$(PYTHON) scripts/download_data.py --days $(DAYS) --pairs $(PAIRS) --config $(CONFIG_PAPER)

# Testing
test:
	@echo "Running unit tests..."
	pytest tests/ -v

test-coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=user_data/strategies --cov-report=html --cov-report=term

# Backtesting
backtest:
	@echo "Running backtest with strategy: $(STRATEGY)"
	freqtrade backtesting \
		--strategy $(STRATEGY) \
		--config $(CONFIG_PAPER) \
		--export trades \
		--export-filename reports/backtest_trades.csv \
		--breakdown day week month

backtest-fast:
	@echo "Running quick backtest (30 days)..."
	freqtrade backtesting \
		--strategy $(STRATEGY) \
		--config $(CONFIG_PAPER) \
		--timerange 20240101-20240201 \
		--export trades \
		--export-filename reports/backtest_quick.csv

backtest-plot:
	@echo "Generating backtest plot..."
	freqtrade plot-dataframe \
		--strategy $(STRATEGY) \
		--config $(CONFIG_PAPER) \
		--pairs BTC/USD \
		--indicators1 don_upper_entry,don_lower_entry,ema \
		--indicators2 rsi \
		--indicators3 atr

# Hyperoptimization
hyperopt:
	@echo "Running hyperoptimization..."
	freqtrade hyperopt \
		--strategy $(STRATEGY) \
		--hyperopt-loss SharpeHyperOptLossDaily \
		--spaces buy sell roi stoploss trailing \
		--config $(CONFIG_PAPER) \
		--epochs 500

hyperopt-quick:
	@echo "Running quick hyperopt (100 epochs)..."
	freqtrade hyperopt \
		--strategy $(STRATEGY) \
		--hyperopt-loss SharpeHyperOptLossDaily \
		--spaces buy sell \
		--config $(CONFIG_PAPER) \
		--epochs 100

hyperopt-show:
	@echo "Showing hyperopt results..."
	freqtrade hyperopt-show --config $(CONFIG_PAPER)

# Trading
trade-paper:
	@echo "Starting paper trading..."
	@echo "Web UI will be available at: http://localhost:8080"
	@echo "Username: freqtrade, Password: freqtrade"
	@echo ""
	@echo "Press Ctrl+C to stop trading"
	freqtrade trade --config $(CONFIG_PAPER) --strategy $(STRATEGY)

trade-live:
	@echo "!!! LIVE TRADING MODE !!!"
	@echo "This will trade with REAL MONEY!"
	@echo ""
	@set /p confirm="Type 'YES' to confirm live trading: "
	@if "$(confirm)"=="YES" (freqtrade trade --config $(CONFIG_LIVE) --strategy $(STRATEGY)) else (echo "Live trading cancelled.")

stop:
	@echo "Stopping all Freqtrade processes..."
	@taskkill /F /IM freqtrade.exe 2>nul || echo "No Freqtrade processes found"

# Analysis and reporting
export:
	@echo "Exporting trades to CSV..."
	$(PYTHON) scripts/export_trades.py --config $(CONFIG_PAPER)

export-live:
	@echo "Exporting live trades to CSV..."
	$(PYTHON) scripts/export_trades.py --config $(CONFIG_LIVE) --output reports/trades_live.csv

mc:
	@echo "Running Monte Carlo bootstrap analysis..."
	$(PYTHON) scripts/mc_bootstrap.py --trades reports/trades_export.csv --simulations 5000

mc-quick:
	@echo "Running quick Monte Carlo analysis..."
	$(PYTHON) scripts/mc_bootstrap.py --trades reports/trades_export.csv --simulations 1000

plot-results:
	@echo "Generating performance plots..."
	freqtrade plot-profit --config $(CONFIG_PAPER) --trade-source file --exportfilename reports/backtest_trades.csv

# Utilities
status:
	@echo "Checking bot status..."
	freqtrade show_trades --config $(CONFIG_PAPER) --db-url sqlite:///user_data/trades.paper.sqlite

balance:
	@echo "Checking account balance..."
	freqtrade balance --config $(CONFIG_PAPER)

validate:
	@echo "Validating strategy and configuration..."
	freqtrade list-strategies --config $(CONFIG_PAPER) --strategy $(STRATEGY)
	freqtrade show-trades --config $(CONFIG_PAPER) --trade-ids 1 2>/dev/null || echo "No trades found (expected for new setup)"

logs:
	@echo "Showing recent logs..."
	@if exist user_data\logs\freqtrade.log (type user_data\logs\freqtrade.log | findstr /C:"ERROR" /C:"WARNING" /C:"INFO") else (echo "No log file found")

# Maintenance
clean:
	@echo "Cleaning temporary files..."
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist user_data\strategies\__pycache__ rmdir /s /q user_data\strategies\__pycache__
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist htmlcov rmdir /s /q htmlcov
	@for /d %%i in (*.egg-info) do @if exist "%%i" rmdir /s /q "%%i"
	@echo "Cleanup complete"

clean-data:
	@echo "WARNING: This will delete all downloaded data!"
	@set /p confirm="Type 'YES' to confirm: "
	@if "$(confirm)"=="YES" (if exist user_data\data rmdir /s /q user_data\data && echo "Data deleted") else (echo "Data deletion cancelled")

# Development helpers
dev-setup: setup
	@echo "Installing development dependencies..."
	pip install jupyter matplotlib seaborn plotly

notebook:
	@echo "Starting Jupyter notebook..."
	jupyter notebook

# Quick start sequence
quickstart: setup data backtest
	@echo ""
	@echo "Quick start complete!"
	@echo "1. Review backtest results in reports/"
	@echo "2. Run 'make trade-paper' to start paper trading"
	@echo "3. Monitor at http://localhost:8080"

# Emergency stop all
emergency-stop:
	@echo "EMERGENCY STOP - Killing all trading processes..."
	@taskkill /F /IM freqtrade.exe 2>nul || echo "No processes found"
	@taskkill /F /IM python.exe /FI "WINDOWTITLE eq freqtrade*" 2>nul || echo "No Python processes found"
	@echo "Emergency stop complete"
