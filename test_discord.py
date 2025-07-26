#!/usr/bin/env python3
"""Test Discord webhook connectivity"""

import requests
import json
from datetime import datetime

def test_discord_webhook():
    webhook_url = 'https://discord.com/api/webhooks/1398566969795416064/mjEtq_BoHhIys1TIEdy7IWuGfl-YMyxIbZNztf65MTJQgAytF-FfTEWdKBey7MetlTpq'
    
    # Create test message
    data = {
        'content': '🤖 **Freqtrade Bot Test**',
        'embeds': [{
            'title': 'Discord Integration Test',
            'description': 'Testing webhook connection before starting the trading bot',
            'color': 0x00ff00,  # Green color
            'fields': [
                {'name': '📊 Status', 'value': 'Webhook Active', 'inline': True},
                {'name': '⏰ Time', 'value': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'inline': True},
                {'name': '🎯 Ready', 'value': 'Bot is ready to start trading!', 'inline': False}
            ],
            'footer': {'text': 'Freqtrade Crypto Bot v1.0'}
        }]
    }
    
    try:
        # Send test message
        response = requests.post(webhook_url, json=data)
        print(f'Status Code: {response.status_code}')
        
        if response.status_code == 204:
            print('✅ Discord webhook test successful!')
            print('Check your Discord channel for the test message.')
        else:
            print(f'❌ Error: {response.text}')
            
    except Exception as e:
        print(f'❌ Exception occurred: {e}')

if __name__ == '__main__':
    test_discord_webhook()
