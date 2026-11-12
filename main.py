#!/usr/bin/env python3
"""
BTC Race Bot - Dip-buy swing bot for cbBTC
Buys dips, sells on recovery. Simple strategy based on top performers.
"""

import json
import os
from pathlib import Path

INPUT_DIR = Path("/input")
OUTPUT_DIR = Path("/output")


def get_price_data():
    """Read price data from input."""
    prices = []
    if INPUT_DIR.exists():
        for f in sorted(INPUT_DIR.iterdir()):
            if f.suffix == '.json':
                try:
                    data = json.loads(f.read_text())
                    if isinstance(data, list):
                        prices = data
                        break
                    elif isinstance(data, dict) and 'prices' in data:
                        prices = data['prices']
                        break
                except:
                    pass
    return prices


def run_bot():
    prices = get_price_data()
    
    if not prices or len(prices) < 60:
        # Not enough data, output no trade
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_DIR / "trade.json", 'w') as f:
            json.dump({"action": "wait", "reason": "insufficient_data"}, f)
        return
    
    # Parameters (based on top performers)
    lookback = 60  # bars to look back for dip
    dip_threshold = 0.0045  # 45bp = 0.45% dip
    tp = 0.0070  # 70bp take profit
    sl = 0.0050  # 50bp stop loss
    max_trades = 3
    
    # State
    state_file = OUTPUT_DIR / "state.json"
    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except:
            pass
    
    position = state.get('position', None)
    trades_done = state.get('trades_done', 0)
    
    # Calculate indicators
    current_price = prices[-1]
    recent_high = max(prices[-lookback:]) if len(prices) >= lookback else max(prices)
    recent_low = min(prices[-lookback:])
    
    dip_pct = (recent_high - current_price) / recent_high if recent_high > 0 else 0
    avg_price = sum(prices[-20:]) / 20 if len(prices) >= 20 else current_price
    trend = "up" if current_price > avg_price else "down"
    
    action = "wait"
    reason = ""
    
    if position is None:
        # Look for dip buy opportunity
        if dip_pct >= dip_threshold and trend == "up" and trades_done < max_trades:
            # Buy at current price
            action = "buy"
            reason = f"dip={dip_pct*100:.2f}%, trend=up, price={current_price}"
            position = {
                "action": "buy",
                "price": current_price,
                "time": len(prices) - 1,
                "stop_loss": current_price * (1 - sl),
                "take_profit": current_price * (1 + tp)
            }
            trades_done += 1
        elif dip_pct >= dip_threshold * 1.5:
            # Deeper dip, buy even in unclear trend
            action = "buy"
            reason = f"deep_dip={dip_pct*100:.2f}%, price={current_price}"
            position = {
                "action": "buy",
                "price": current_price,
                "time": len(prices) - 1,
                "stop_loss": current_price * (1 - sl),
                "take_profit": current_price * (1 + tp)
            }
            trades_done += 1
        else:
            reason = f"no_dip (dip={dip_pct*100:.2f}%, need={dip_threshold*100:.2f}%)"
    else:
        # Check exit conditions
        pnl = (current_price - position['price']) / position['price']
        
        if current_price <= position['stop_loss']:
            action = "sell"
            reason = f"stop_loss hit (pnl={pnl*100:.2f}%)"
        elif current_price >= position['take_profit']:
            action = "sell"
            reason = f"take_profit hit (pnl={pnl*100:.2f}%)"
        elif len(prices) - position['time'] > 120:
            # Time exit after 120 bars
            action = "sell"
            reason = f"time_exit (held={len(prices)-position['time']} bars, pnl={pnl*100:.2f}%)"
        else:
            reason = f"holding (pnl={pnl*100:.2f}%)"
    
    # Save state
    state = {
        "position": position,
        "trades_done": trades_done,
        "last_price": current_price,
        "action": action,
        "reason": reason
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2))
    
    # Output trade decision
    with open(OUTPUT_DIR / "trade.json", 'w') as f:
        json.dump({
            "action": action,
            "price": current_price,
            "reason": reason,
            "position": position,
            "trades_done": trades_done
        }, f, indent=2)
    
    print(f"Action: {action}")
    print(f"Price: {current_price}")
    print(f"Reason: {reason}")
    print(f"Trades done: {trades_done}")


if __name__ == "__main__":
    run_bot()
