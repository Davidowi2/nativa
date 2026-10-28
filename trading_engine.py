#!/usr/bin/env python3
"""
Nativa — Trading Engine
Uses the fine-tuned model (via llama.cpp) to make trading decisions

Usage:
    python trading_engine.py --model http://localhost:8080 --symbol EURUSD --interval 3600
"""

import argparse
import json
import time
import sqlite3
import urllib.request
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Configuration
LLAMA_URL = "http://localhost:8080/v1/chat/completions"
DB_PATH = "data/nativa_trades.db"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8077145837")

# Risk management (inherited from prior research)
MAX_POSITIONS = 1
RISK_PER_TRADE = 0.005  # 0.5%
DAILY_LOSS_LIMIT = 0.04  # 4%
TOTAL_DRAWDOWN = 0.06  # 6%
NEWS_BLACKOUT_MIN = 2  # minutes before/after high-impact news


def init_db():
    """Initialize SQLite database for trade logging."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            decision TEXT NOT NULL,
            confidence REAL,
            reasoning TEXT,
            entry_price REAL,
            stop_loss REAL,
            take_profit REAL,
            position_size REAL,
            pnl REAL,
            exit_reason TEXT,
            status TEXT DEFAULT 'open'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            parsed_decision TEXT,
            latency_ms INTEGER
        )
    """)
    conn.commit()
    return conn


def get_market_data(symbol):
    """Fetch current market data for a symbol.
    
    In production, this would fetch from TradeLocker or a data provider.
    For now, returns a placeholder that the user fills in.
    """
    # TODO: Integrate with TradeLocker quotes API
    # or Dukascopy for historical, or a live data feed
    return {
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "open": 0.0,
        "high": 0.0,
        "low": 0.0,
        "close": 0.0,
        "volume": 0,
        "rsi": 50.0,
        "sma20": 0.0,
        "atr": 0.001,
    }


def build_prompt(market_data):
    """Build the prompt for the model."""
    return (
        f"Market: {market_data['symbol']} H1\n"
        f"Date: {market_data['timestamp']}\n"
        f"Open: {market_data['open']:.4f}, High: {market_data['high']:.4f}, "
        f"Low: {market_data['low']:.4f}, Close: {market_data['close']:.4f}\n"
        f"Volume: {market_data['volume']}\n"
        f"RSI(14): {market_data['rsi']:.1f}\n"
        f"SMA20: {market_data['sma20']:.4f}\n"
        f"ATR(14): {market_data['atr']:.4f}\n"
        f"\nWhat is your trading decision?"
    )


def query_model(prompt, model_url):
    """Query the llama.cpp server for a trading decision."""
    payload = {
        "model": "nativa",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Nativa, a trading decision engine. You analyze market data "
                    "and make trading decisions with reasoning. You never refuse to analyze "
                    "a market. You always provide a decision (BUY/SELL/HOLD) with confidence "
                    "and reasoning. You consider risk management in every decision. "
                    "Max risk per trade: 0.5%. Stop loss: 1.5x ATR. Take profit: 3x ATR. "
                    "No trading during news events (2 min blackout)."
                )
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 500,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    
    start = time.time()
    req = urllib.request.Request(
        model_url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
    latency = int((time.time() - start) * 1000)
    
    content = result["choices"][0]["message"]["content"]
    return content, latency


def parse_decision(response):
    """Parse the model's response into a structured decision."""
    decision = "HOLD"
    confidence = 0.5
    reasoning = ""
    risk = ""
    
    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("Decision:"):
            decision = line.split(":", 1)[1].strip().upper()
        elif line.startswith("Confidence:"):
            try:
                confidence = float(line.split(":", 1)[1].strip())
            except ValueError:
                confidence = 0.5
        elif line.startswith("Reasoning:"):
            reasoning = line.split(":", 1)[1].strip()
        elif line.startswith("Risk:"):
            risk = line.split(":", 1)[1].strip()
    
    # Validate decision
    if decision not in ("BUY", "SELL", "HOLD"):
        decision = "HOLD"
    
    return {
        "decision": decision,
        "confidence": confidence,
        "reasoning": reasoning,
        "risk": risk,
    }


def send_telegram(message):
    """Send a Telegram alert."""
    if not TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Nativa Trading Engine")
    parser.add_argument("--model", default=LLAMA_URL, help="llama.cpp server URL")
    parser.add_argument("--symbol", default="EURUSD", help="Trading symbol")
    parser.add_argument("--interval", type=int, default=3600, help="Polling interval (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="Don't execute trades")
    args = parser.parse_args()
    
    conn = init_db()
    print(f"Nativa Trading Engine started")
    print(f"Model: {args.model}")
    print(f"Symbol: {args.symbol}")
    print(f"Interval: {args.interval}s")
    print(f"Dry run: {args.dry_run}")
    
    send_telegram(f"🤖 Nativa started\nSymbol: {args.symbol}\nInterval: {args.interval}s")
    
    while True:
        try:
            # Get market data
            market_data = get_market_data(args.symbol)
            prompt = build_prompt(market_data)
            
            # Query model
            response, latency = query_model(prompt, args.model)
            parsed = parse_decision(response)
            
            # Log signal
            conn.execute(
                "INSERT INTO signals (timestamp, symbol, prompt, response, parsed_decision, latency_ms) VALUES (?, ?, ?, ?, ?, ?)",
                (market_data["timestamp"], args.symbol, prompt, response, parsed["decision"], latency)
            )
            conn.commit()
            
            print(f"\n[{market_data['timestamp']}] {args.symbol}")
            print(f"  Decision: {parsed['decision']} (conf: {parsed['confidence']:.2f})")
            print(f"  Reasoning: {parsed['reasoning'][:100]}...")
            print(f"  Latency: {latency}ms")
            
            # Execute trade if not HOLD and not dry-run
            if parsed["decision"] != "HOLD" and not args.dry_run:
                # TODO: Integrate with TradeLocker
                # For now, just log and alert
                conn.execute(
                    "INSERT INTO trades (timestamp, symbol, decision, confidence, reasoning, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (market_data["timestamp"], args.symbol, parsed["decision"],
                     parsed["confidence"], parsed["reasoning"], "pending")
                )
                conn.commit()
                
                send_telegram(
                    f"📊 Nativa Signal\n"
                    f"Symbol: {args.symbol}\n"
                    f"Decision: {parsed['decision']}\n"
                    f"Confidence: {parsed['confidence']:.2f}\n"
                    f"Reasoning: {parsed['reasoning'][:200]}"
                )
            
            time.sleep(args.interval)
            
        except KeyboardInterrupt:
            print("\nShutting down...")
            send_telegram("🛑 Nativa stopped")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()