#!/usr/bin/env python3
"""
Setup Validation Script

Validates that the Freqtrade crypto bot environment is properly configured.
"""

import os
import sys
import importlib.util
import json
from pathlib import Path

def check_python_version():
    """Check Python version is 3.11+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("❌ Python 3.11+ required, found {}.{}.{}".format(version.major, version.minor, version.micro))
        return False
    print("✅ Python {}.{}.{} - OK".format(version.major, version.minor, version.micro))
    return True

def check_dependencies():
    """Check required dependencies are installed"""
    required_packages = [
        'freqtrade', 'pandas', 'numpy', 'talib', 'matplotlib', 
        'seaborn', 'scipy', 'pytest', 'dotenv'
    ]
    
    missing = []
    for package in required_packages:
        try:
            if package == 'dotenv':
                importlib.import_module('dotenv')
            else:
                importlib.import_module(package)
            print(f"✅ {package} - OK")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing.append(package)
    
    return len(missing) == 0

def check_env_file():
    """Check .env file exists and has required variables"""
    env_path = Path('.env')
    
    if not env_path.exists():
        print("❌ .env file not found - copy .env.example to .env")
        return False
    
    print("✅ .env file exists")
    
    # Check required variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['CB_KEY', 'CB_SECRET', 'CB_PASSPHRASE']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith('your_'):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Please set these variables in .env: {', '.join(missing_vars)}")
        return False
    
    print("✅ Required environment variables configured")
    return True

def check_strategy_file():
    """Check strategy file exists and is valid"""
    strategy_path = Path('user_data/strategies/donchian_atr.py')
    
    if not strategy_path.exists():
        print("❌ Strategy file not found")
        return False
    
    print("✅ Strategy file exists")
    
    # Try to import strategy
    try:
        spec = importlib.util.spec_from_file_location("donchian_atr", strategy_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'DonchianATRTrend'):
            print("✅ Strategy class found")
            return True
        else:
            print("❌ DonchianATRTrend class not found in strategy file")
            return False
    except Exception as e:
        print(f"❌ Error importing strategy: {e}")
        return False

def check_config_files():
    """Check configuration files are valid"""
    config_files = ['user_data/config.paper.json', 'user_data/config.live.json']
    
    for config_file in config_files:
        config_path = Path(config_file)
        
        if not config_path.exists():
            print(f"❌ {config_file} not found")
            return False
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"✅ {config_file} - valid JSON")
        except json.JSONDecodeError as e:
            print(f"❌ {config_file} - invalid JSON: {e}")
            return False
    
    return True

def check_directories():
    """Check required directories exist"""
    required_dirs = [
        'user_data', 'user_data/strategies', 'scripts', 'tests', 'reports'
    ]
    
    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            print(f"❌ Directory {dir_path} not found")
            return False
        print(f"✅ Directory {dir_path} exists")
    
    return True

def main():
    """Run all validation checks"""
    print("🔍 Validating Freqtrade Crypto Bot Setup")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Environment File", check_env_file),
        ("Strategy File", check_strategy_file),
        ("Config Files", check_config_files),
        ("Directories", check_directories),
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n📋 Checking {check_name}:")
        result = check_func()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("🎉 ALL CHECKS PASSED!")
        print("\nNext steps:")
        print("1. Run 'make data' to download historical data")
        print("2. Run 'make backtest' to test strategy")
        print("3. Run 'make trade-paper' to start paper trading")
    else:
        print(f"❌ {total - passed} checks failed out of {total}")
        print("\nPlease fix the issues above before proceeding.")
        sys.exit(1)

if __name__ == "__main__":
    main()
