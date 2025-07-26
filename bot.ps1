# Freqtrade Crypto Bot - Windows PowerShell Script
# Professional Trading Bot Setup and Management

param(
    [string]$Command = "help",
    [string]$Config = "config.alpaca.paper.json",
    [string]$Strategy = "DonchianATRTrend"
)

$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host "Freqtrade Crypto Bot - Windows Commands" -ForegroundColor Green
    Write-Host "=======================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\bot.ps1 -Command <command> [options]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Available Commands:" -ForegroundColor Cyan
    Write-Host "  setup         - Install dependencies and setup environment"
    Write-Host "  data          - Download historical data"
    Write-Host "  backtest      - Run strategy backtest"
    Write-Host "  hyperopt      - Run parameter optimization"
    Write-Host "  trade-paper   - Start paper trading"
    Write-Host "  trade-live    - Start live trading"
    Write-Host "  export        - Export trades to CSV"
    Write-Host "  mc            - Run Monte Carlo analysis"
    Write-Host "  test          - Run unit tests"
    Write-Host "  monitor       - Monitor bot health"
    Write-Host "  status        - Show bot status"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\bot.ps1 -Command setup"
    Write-Host "  .\bot.ps1 -Command backtest -Strategy DonchianATRTrend"
    Write-Host "  .\bot.ps1 -Command trade-paper -Config config.paper.json"
}

function Test-Prerequisites {
    Write-Host "Checking prerequisites..." -ForegroundColor Yellow
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-Host "✓ Python: $pythonVersion" -ForegroundColor Green
    } catch {
        Write-Host "✗ Python not found. Please install Python 3.11" -ForegroundColor Red
        exit 1
    }
    
    # Check if .env exists
    if (-not (Test-Path ".env")) {
        Write-Host "⚠ .env file not found. Copying from .env.example..." -ForegroundColor Yellow
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-Host "✓ .env file created. Please edit it with your API keys." -ForegroundColor Green
        } else {
            Write-Host "✗ .env.example not found" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "✓ .env file exists" -ForegroundColor Green
    }
}

function Install-Dependencies {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    
    # Check if Poetry is available
    try {
        poetry --version | Out-Null
        Write-Host "✓ Poetry found, using Poetry for dependency management" -ForegroundColor Green
        poetry install --extras talib
    } catch {
        Write-Host "⚠ Poetry not found, using pip..." -ForegroundColor Yellow
        
        # Upgrade pip
        python -m pip install --upgrade pip
        
        # Install requirements
        python -m pip install -r requirements.txt
        
        Write-Host ""
        Write-Host "Note: You may need to manually install TA-Lib for Windows:" -ForegroundColor Yellow
        Write-Host "1. Download wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib" -ForegroundColor Cyan
        Write-Host "2. pip install TA_Lib-0.4.28-cp311-cp311-win_amd64.whl" -ForegroundColor Cyan
    }
    
    # Create user_data directories
    Write-Host "Setting up Freqtrade directories..." -ForegroundColor Yellow
    try {
        freqtrade create-userdir --userdir user_data
        Write-Host "✓ Freqtrade directories created" -ForegroundColor Green
    } catch {
        Write-Host "⚠ Freqtrade create-userdir failed, but continuing..." -ForegroundColor Yellow
    }
}

function Download-Data {
    Write-Host "Downloading historical data..." -ForegroundColor Yellow
    
    $pairs = @("AAPL/USD", "TSLA/USD", "SPY/USD")
    $timeframe = "1h"
    $days = 365
    
    python scripts/download_data.py --exchange alpaca --pairs $pairs --timeframe $timeframe --days $days --config $Config
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Data download completed" -ForegroundColor Green
    } else {
        Write-Host "✗ Data download failed" -ForegroundColor Red
        exit 1
    }
}

function Run-Backtest {
    Write-Host "Running backtest with $Strategy strategy..." -ForegroundColor Yellow
    
    freqtrade backtesting --config $Config --strategy $Strategy --timeframe 1h --timerange 20231201-20241201 --export trades,signals --cache none
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Backtest completed successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Backtest failed" -ForegroundColor Red
        exit 1
    }
}

function Run-Hyperopt {
    Write-Host "Running hyperparameter optimization..." -ForegroundColor Yellow
    Write-Host "This may take several hours to complete..." -ForegroundColor Cyan
    
    freqtrade hyperopt --config $Config --strategy $Strategy --timeframe 1h --timerange 20231201-20241201 --hyperopt-loss SharpeHyperOptLoss --spaces buy sell --epochs 300 --jobs 1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Hyperopt completed successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Hyperopt failed" -ForegroundColor Red
        exit 1
    }
}

function Start-PaperTrading {
    Write-Host "Starting paper trading (dry run)..." -ForegroundColor Yellow
    Write-Host "Press Ctrl+C to stop the bot" -ForegroundColor Cyan
    
    freqtrade trade --config config.alpaca.paper.json --strategy $Strategy
}

function Start-LiveTrading {
    Write-Host "WARNING: Starting LIVE trading with real money!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure you have:" -ForegroundColor Yellow
    Write-Host "  1. ✓ Tested thoroughly with paper trading"
    Write-Host "  2. ✓ Set appropriate stake amounts in config.alpaca.live.json"
    Write-Host "  3. ✓ Added your API keys to .env"
    Write-Host "  4. ✓ Verified the strategy is working correctly"
    Write-Host ""
    
    $confirmation = Read-Host "Type 'YES' to confirm live trading"
    
    if ($confirmation -eq "YES") {
        Write-Host "Starting live trading..." -ForegroundColor Green
        freqtrade trade --config config.alpaca.live.json --strategy $Strategy
    } else {
        Write-Host "Live trading cancelled." -ForegroundColor Yellow
    }
}

function Export-Trades {
    Write-Host "Exporting trades to CSV with R-multiples..." -ForegroundColor Yellow
    
    python scripts/export_trades.py --db-url "sqlite:///user_data/trades.sqlite" --output "reports/trades.csv" --risk-unit 5.0
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Trades exported successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Trade export failed" -ForegroundColor Red
        exit 1
    }
}

function Run-MonteCarlo {
    Write-Host "Running Monte Carlo bootstrap analysis..." -ForegroundColor Yellow
    
    # First export trades
    Export-Trades
    
    # Then run Monte Carlo
    python scripts/mc_bootstrap.py --input "reports/trades.csv" --simulations 10000 --output-dir reports
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Monte Carlo analysis completed" -ForegroundColor Green
        Write-Host "Check reports/ directory for results" -ForegroundColor Cyan
    } else {
        Write-Host "✗ Monte Carlo analysis failed" -ForegroundColor Red
        exit 1
    }
}

function Run-Tests {
    Write-Host "Running unit tests..." -ForegroundColor Yellow
    
    python -m pytest tests/ -v --tb=short
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ All tests passed" -ForegroundColor Green
    } else {
        Write-Host "✗ Some tests failed" -ForegroundColor Red
        exit 1
    }
}

function Monitor-Bot {
    Write-Host "Monitoring bot health..." -ForegroundColor Yellow
    
    python scripts/monitor_bot.py --config $Config
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Health check completed" -ForegroundColor Green
    } else {
        Write-Host "✗ Health check failed" -ForegroundColor Red
        exit 1
    }
}

function Show-Status {
    Write-Host "Bot Status Summary" -ForegroundColor Green
    Write-Host "==================" -ForegroundColor Green
    Write-Host ""
    
    # Check if config files exist
    $configs = @("config.alpaca.paper.json", "config.alpaca.live.json")
    foreach ($configFile in $configs) {
        if (Test-Path $configFile) {
            Write-Host "✓ $configFile exists" -ForegroundColor Green
        } else {
            Write-Host "✗ $configFile missing" -ForegroundColor Red
        }
    }
    
    # Check if strategy exists
    if (Test-Path "user_data/strategies/donchian_atr.py") {
        Write-Host "✓ DonchianATRTrend strategy exists" -ForegroundColor Green
    } else {
        Write-Host "✗ Strategy file missing" -ForegroundColor Red
    }
    
    # Check if data exists
    if (Test-Path "user_data/data") {
        $dataFiles = Get-ChildItem "user_data/data" -Recurse -Filter "*.json" | Measure-Object
        Write-Host "✓ Data directory contains $($dataFiles.Count) files" -ForegroundColor Green
    } else {
        Write-Host "✗ No data directory found" -ForegroundColor Red
    }
    
    # Check database
    if (Test-Path "user_data/trades.sqlite") {
        Write-Host "✓ Trades database exists" -ForegroundColor Green
    } else {
        Write-Host "⚠ No trades database (normal for new setup)" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Run '.\bot.ps1 -Command monitor' for detailed health check" -ForegroundColor Cyan
}

# Main script execution
Write-Host "Freqtrade Crypto Bot Manager" -ForegroundColor Magenta
Write-Host "============================" -ForegroundColor Magenta
Write-Host ""

switch ($Command.ToLower()) {
    "help" { Show-Help }
    "setup" { 
        Test-Prerequisites
        Install-Dependencies 
        Write-Host ""
        Write-Host "Setup complete! Next steps:" -ForegroundColor Green
        Write-Host "1. Edit .env file with your API keys" -ForegroundColor Cyan
        Write-Host "2. Run: .\bot.ps1 -Command data" -ForegroundColor Cyan
        Write-Host "3. Run: .\bot.ps1 -Command backtest" -ForegroundColor Cyan
    }
    "data" { Download-Data }
    "backtest" { Run-Backtest }
    "hyperopt" { Run-Hyperopt }
    "trade-paper" { Start-PaperTrading }
    "trade-live" { Start-LiveTrading }
    "export" { Export-Trades }
    "mc" { Run-MonteCarlo }
    "test" { Run-Tests }
    "monitor" { Monitor-Bot }
    "status" { Show-Status }
    default { 
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Show-Help 
    }
}
