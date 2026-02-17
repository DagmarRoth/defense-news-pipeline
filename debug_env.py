#!/usr/bin/env python3
import os

print("All Environment Variables:")
print("="*70)
env_vars = sorted(os.environ.items())
for key, value in env_vars:
    if len(value) > 60:
        print(f"{key}: {value[:60]}...")
    else:
        print(f"{key}: {value}")

print("\n" + "="*70)
print("Specifically checking for our variables:")
print("="*70)
our_vars = [
    'ANTHROPIC_API_KEY',
    'SLACK_WEBHOOK_URL', 
    'GOOGLE_SHEETS_SPREADSHEET_ID',
    'SLACK_SCORE_THRESHOLD',
    'POLL_INTERVAL_SECONDS',
    'GOOGLE_CREDENTIALS_PATH'
]

for var in our_vars:
    value = os.getenv(var)
    status = "✓ SET" if value else "✗ NOT SET"
    print(f"{var}: {status}")
