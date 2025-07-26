# Freqtrade Crypto Bot Makefile
# Senior Quant Dev - Professional Trading Bot Setup

.PHONY: help setup setup-poetry setup-pip data backtest hyperopt trade-paper trade-live export mc test clean

# Default target
help:
	@echo "Freqtrade Crypto Bot - Available Commands:"
	@echo "=========================================="
	@echo "  setup         - Install dependencies (auto-detects poetry/pip)"
	@echo "  setup-poetry  - Install dependencies using Poetry"
	@echo "  setup-pip     - Install dependencies using pip"
	@echo "  data          - Download historical data"
	@echo "  backtest      - Run backtest with DonchianATRTrend strategy"
	@echo "  hyperopt      - Run hyperparameter optimization"
	@echo "  trade-paper   - Start paper trading (dry run)"
	@echo "  trade-live    - Start live trading (real money!)"
	@echo "  export        - Export trades to CSV with R-multiples"
	@echo "  mc            - Run Monte Carlo analysis"
	@echo "  test          - Run unit tests"
	@echo "  clean         - Clean temporary files"
	@echo ""
	@echo "Environment Setup:"
	@echo "  1. cp .env.example .env && edit .env with your API keys"
	@echo "  2. make setup"
	@echo "  3. make data"
	@echo "  4. make backtest"

# Environment variables
PYTHON := python
CONFIG_PAPER := config.paper.json
CONFIG_LIVE := config.live.json
STRATEGY := DonchianATRTrend
TIMEFRAME := 1h
PAIRS := BTC/USD ETH/USD
DAYS := 365

# Check if poetry is available
setup:
	@if command -v poetry >/dev/null 2>&1; then \
		echo "Poetry detected, using poetry for setup..."; \
		$(MAKE) setup-poetry; \
	else \
		echo "Poetry not found, using pip for setup..."; \
		$(MAKE) setup-pip; \
	fi

# Setup using Poetry (recommended)
setup-poetry:
	@echo "Setting up environment with Poetry..."
	poetry install --extras talib
	@echo "Creating user_data directories..."
	poetry run freqtrade create-userdir --userdir user_data
	@echo ""
	@echo "Setup complete! Next steps:"
	@echo "1. Copy .env.example to .env and add your API keys"
	@echo "2. Run 'make data' to download historical data"
	@echo "3. Run 'make backtest' to test the strategy"

# Setup using pip (fallback)
setup-pip:
	@echo "Setting up environment with pip..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	@echo ""
	@echo "Note: You may need to manually install TA-Lib:"
	@echo "Windows: Download wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib"
	@echo "Linux: sudo apt-get install ta-lib-dev"
	@echo "macOS: brew install ta-lib"
	@echo ""
	@echo "Creating user_data directories..."
	freqtrade create-userdir --userdir user_data
	@echo ""
	@echo "Setup complete! Next steps:"
	@echo "1. Copy .env.example to .env and add your API keys"
	@echo "2. Run 'make data' to download historical data"

# Download historical data
data:
	@echo "Downloading historical data..."
	$(PYTHON) scripts/download_data.py \
		--exchange coinbasepro \
		--pairs $(PAIRS) \
		--timeframe $(TIMEFRAME) \
		--days $(DAYS) \
		--config $(CONFIG_PAPER)

# Run backtest
backtest:
	@echo "Running backtest with $(STRATEGY) strategy..."
	freqtrade backtesting \
		--config $(CONFIG_PAPER) \
		--strategy $(STRATEGY) \
		--timeframe $(TIMEFRAME) \
		--timerange 20231201-20241201 \
		--export trades,signals \
		--cache none

# Run hyperparameter optimization
hyperopt:
	@echo "Running hyperparameter optimization..."
	@echo "This may take several hours to complete..."
	freqtrade hyperopt \
		--config $(CONFIG_PAPER) \
		--strategy $(STRATEGY) \
		--timeframe $(TIMEFRAME) \
		--timerange 20231201-20241201 \
		--hyperopt-loss SharpeHyperOptLoss \
		--spaces buy sell \
		--epochs 300 \
		--jobs 1

# Start paper trading
trade-paper:
	@echo "Starting paper trading (dry run)..."
	@echo "Press Ctrl+C to stop the bot"
	freqtrade trade \
		--config $(CONFIG_PAPER) \
		--strategy $(STRATEGY)

# Start live trading
trade-live:
	@echo "WARNING: Starting LIVE trading with real money!"
	@echo "Make sure you have:"
	@echo "  1. Tested thoroughly with paper trading"
	@echo "  2. Set appropriate stake amounts in $(CONFIG_LIVE)"
	@echo "  3. Added your API keys to .env"
	@echo ""
	@read -p "Type 'YES' to confirm live trading: " confirm; \
	if [ "$$confirm" = "YES" ]; then \
		freqtrade trade --config $(CONFIG_LIVE) --strategy $(STRATEGY); \
	else \
		echo "Live trading cancelled."; \
	fi

# Export trades with R-multiples
export:
	@echo "Exporting trades to CSV..."
	$(PYTHON) scripts/export_trades.py \
		--db-url sqlite:///user_data/trades.sqlite \
		--output reports/trades.csv \
		--risk-unit 5.0

# Run Monte Carlo analysis
mc: export
	@echo "Running Monte Carlo bootstrap analysis..."
	$(PYTHON) scripts/mc_bootstrap.py \
		--input reports/trades.csv \
		--simulations 10000 \
		--output-dir reports

# Run unit tests
test:
	@echo "Running unit tests..."
	$(PYTHON) -m pytest tests/ -v --tb=short

# Additional useful commands
plot-dataframe:
	@echo "Plotting strategy indicators..."
	freqtrade plot-dataframe \
		--config $(CONFIG_PAPER) \
		--strategy $(STRATEGY) \
		--pairs BTC/USD \
		--timerange 20241101-20241201 \
		--indicators1 ema_trend don_upper_entry don_lower_entry \
		--indicators2 atr

plot-profit:
	@echo "Plotting profit results..."
	freqtrade plot-profit \
		--config $(CONFIG_PAPER) \
		--strategy $(STRATEGY) \
		--timerange 20241101-20241201

# Show trade analysis
show-trades:
	@echo "Showing trade analysis..."
	freqtrade show-trades \
		--config $(CONFIG_PAPER) \
		--strategy $(STRATEGY) \
		--print-trades

# List downloaded data
list-data:
	@echo "Available data:"
	freqtrade list-data --userdir user_data

# Update strategy
update-strategy:
	@echo "Validating strategy syntax..."
	freqtrade test-pairlist --config $(CONFIG_PAPER) --strategy $(STRATEGY)

# Create new strategy template
new-strategy:
	@read -p "Enter new strategy name: " name; \
	freqtrade new-strategy --strategy $$name --userdir user_data

# Clean temporary files
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name ".DS_Store" -delete
	rm -rf .pytest_cache/
	rm -f user_data/logs/*.log.1
	@echo "Cleanup complete!"

# Monitor logs
logs:
	@echo "Monitoring bot logs (Ctrl+C to stop)..."
	tail -f user_data/logs/freqtrade.log

# Show help for advanced users
advanced-help:
	@echo "Advanced Commands:"
	@echo "=================="
	@echo "  plot-dataframe    - Plot strategy indicators"
	@echo "  plot-profit       - Plot profit/loss charts"
	@echo "  show-trades       - Show detailed trade analysis"
	@echo "  list-data         - List available data files"
	@echo "  update-strategy   - Validate strategy syntax"
	@echo "  new-strategy      - Create new strategy template"
	@echo "  logs              - Monitor bot logs in real-time"
	@echo ""
	@echo "Configuration:"
	@echo "  CONFIG_PAPER = $(CONFIG_PAPER)"
	@echo "  CONFIG_LIVE = $(CONFIG_LIVE)"
	@echo "  STRATEGY = $(STRATEGY)"
	@echo "  TIMEFRAME = $(TIMEFRAME)"
	@echo "  PAIRS = $(PAIRS)"
