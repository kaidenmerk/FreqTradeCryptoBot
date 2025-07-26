#!/usr/bin/env python3
"""
Check available crypto pairs on Alpaca
"""
import os
import ccxt

# Load environment variables
alpaca_key = os.getenv('ALPACA_KEY', 'PKZPW4OGB8L48YXQHI4A')
alpaca_secret = os.getenv('ALPACA_SECRET', 'zIsxFopw8rYeOmrGmX456W53goaHXbyc5LQ5rZRl')

try:
    exchange = ccxt.alpaca({
        'apiKey': alpaca_key,
        'secret': alpaca_secret,
        'sandbox': True,
        'enableRateLimit': True,
        'urls': {'api': 'https://paper-api.alpaca.markets'}
    })
    
    print("Loading Alpaca markets...")
    markets = exchange.load_markets()
    
    # Find all crypto pairs (typically end with /USD)
    crypto_pairs = []
    for symbol in markets.keys():
        if '/USD' in symbol:
            # Check if it's likely a crypto (not a stock)
            base = symbol.split('/')[0]
            if len(base) <= 5 and base.isupper():  # Crypto tickers are usually short and uppercase
                crypto_pairs.append(symbol)
    
    print(f"\n✅ Available Alpaca Crypto Pairs ({len(crypto_pairs)} total):")
    for pair in sorted(crypto_pairs):
        print(f"  {pair}")
        
    # Create a reasonable subset for trading (top cryptos)
    priority_cryptos = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'MATIC/USD', 'AVAX/USD', 
                       'LTC/USD', 'DOGE/USD', 'ADA/USD', 'DOT/USD', 'LINK/USD',
                       'UNI/USD', 'AAVE/USD', 'ALGO/USD', 'ATOM/USD', 'FIL/USD']
    
    available_priority = [pair for pair in priority_cryptos if pair in crypto_pairs]
    
    print(f"\n🎯 Recommended trading pairs ({len(available_priority)}):")
    for pair in available_priority:
        print(f"  {pair}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("Make sure ALPACA_KEY and ALPACA_SECRET are set correctly")
