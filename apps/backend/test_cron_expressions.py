#!/usr/bin/env python3
"""Test different cron expressions to see which ones work"""

from croniter import croniter
from datetime import datetime

test_expressions = [
    "*/5 * * * *",      # Every 5 minutes (standard)
    "0/5 * * * *",      # Every 5 minutes starting at 0 (alternative)
    "0 */5 * * *",      # At minute 0 past every 5th hour
    "5 * * * *",        # At minute 5 of every hour
    "0 0/5 * * *",      # At minute 0 past every 5th hour
]

print("Testing cron expressions with croniter:\n")
for expr in test_expressions:
    try:
        cron = croniter(expr, datetime.now())
        next_run = cron.get_next(datetime)
        print(f"✅ '{expr}' - Valid")
        print(f"   Next run: {next_run}")
    except Exception as e:
        print(f"❌ '{expr}' - Invalid: {e}")
    print()

# Test what the workflow agent generated
print("\nTesting workflow agent's expression:")
agent_expr = "0/5 * * * *"
try:
    cron = croniter(agent_expr, datetime.now())
    next_run = cron.get_next(datetime)
    print(f"✅ '{agent_expr}' - Valid (from logs)")
    print(f"   Next run: {next_run}")
except Exception as e:
    print(f"❌ '{agent_expr}' - Invalid: {e}")