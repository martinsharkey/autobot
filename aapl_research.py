#!/usr/bin/env python3
"""Research AAPL stock: technical indicators, recent price action, and a trading signal."""

import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta

# Fetch 6 months of daily data for enough SMA history
ticker = yf.Ticker("AAPL")
hist = ticker.history(period="6mo")

if hist.empty:
    print("No data retrieved")
    exit(1)

# --- Current price info ---
latest = hist.iloc[-1]
prev_close = hist.iloc[-2]["Close"]
current_price = latest["Close"]
change = current_price - prev_close
change_pct = (change / prev_close) * 100
high_52w = hist["High"].rolling(window=126).max().iloc[-1]
low_52w = hist["Low"].rolling(window=126).min().iloc[-1]

# --- Moving Averages ---
sma_20 = hist["Close"].rolling(window=20).mean().iloc[-1]
sma_50 = hist["Close"].rolling(window=50).mean().iloc[-1]
sma_200 = hist["Close"].rolling(window=200).mean().iloc[-1]

# --- RSI (14-day) ---
delta = hist["Close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.rolling(window=14).mean()
avg_loss = loss.rolling(window=14).mean()
rs = avg_gain / avg_loss
rsi = 100 - (100 / (1 + rs)).iloc[-1]

# --- MACD ---
ema_12 = hist["Close"].ewm(span=12).mean()
ema_26 = hist["Close"].ewm(span=26).mean()
macd_line = ema_12 - ema_26
signal_line = macd_line.ewm(span=9).mean()
macd_hist = macd_line - signal_line
macd_val = macd_line.iloc[-1]
signal_val = signal_line.iloc[-1]
macd_h_val = macd_hist.iloc[-1]

# --- Volume analysis ---
avg_volume_20 = hist["Volume"].rolling(window=20).mean().iloc[-1]
latest_volume = latest["Volume"]
volume_spike = latest_volume > avg_volume_20 * 1.5

# --- Recent performance ---
one_week_ago = hist.iloc[-6]["Close"] if len(hist) >= 6 else hist.iloc[0]["Close"]
one_month_ago = hist.iloc[-22]["Close"] if len(hist) >= 22 else hist.iloc[0]["Close"]
week_change = ((current_price - one_week_ago) / one_week_ago) * 100
month_change = ((current_price - one_month_ago) / one_month_ago) * 100

# --- Generate signal ---
signals = []
score = 0

# Trend following
if current_price > sma_20 > sma_50 > sma_200:
    signals.append("Strong uptrend (price > SMA20 > SMA50 > SMA200)")
    score += 2
elif current_price > sma_50 and sma_50 > sma_200:
    signals.append("Moderate uptrend (price > SMA50 > SMA200)")
    score += 1
elif current_price < sma_20 < sma_50 < sma_200:
    signals.append("Strong downtrend (price < SMA20 < SMA50 < SMA200)")
    score -= 2
elif current_price < sma_50:
    signals.append("Below SMA50 — bearish bias")
    score -= 1

# RSI
if rsi > 70:
    signals.append(f"RSI {rsi:.1f} — Overbought territory (caution)")
    score -= 1
elif rsi < 30:
    signals.append(f"RSI {rsi:.1f} — Oversold territory (potential bounce)")
    score += 1
else:
    signals.append(f"RSI {rsi:.1f} — Neutral")

# MACD
if macd_val > signal_val and macd_h_val > 0:
    signals.append("MACD bullish (line above signal, histogram positive)")
    score += 1
elif macd_val < signal_val and macd_h_val < 0:
    signals.append("MACD bearish (line below signal, histogram negative)")
    score -= 1

# Volume
if volume_spike and change_pct > 0:
    signals.append(f"Volume spike (+{volume_spike[0] if isinstance(volume_spike, pd.Series) else ''}above avg) with positive price — bullish confirmation" if isinstance(volume_spike, pd.Series) else "")
    score += 1 if "bullish" else 0
elif volume_spike and change_pct < 0:
    signals.append("Volume spike with negative price — bearish confirmation")
    score -= 1

# 52-week proximity
price_position = ((current_price - low_52w) / (high_52w - low_52w)) * 100 if high_52w != low_52w else 50

if price_position > 80 and score < 0:
    signals.append(f"Near 52-week high ({price_position:.0f}% of range) + bearish indicators — possible top")
    score -= 1
elif price_position < 20 and score > 0:
    signals.append(f"Near 52-week low ({price_position:.0f}% of range) + bullish indicators — possible bottom")
    score += 1

# Final signal
if score >= 2:
    signal = "BUY 🟢"
elif score >= 1:
    signal = "BUY (cautious) 🟡"
elif score <= -2:
    signal = "SELL 🔴"
elif score <= -1:
    signal = "SELL (cautious) 🟠"
else:
    signal = "HOLD / NEUTRAL ⚪"

# --- Output ---
print(f"AAPL Trading Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"{'='*60}")
print(f"Current Price:  ${current_price:.2f}  ({change_pct:+.2f}% today)")
print(f"52-Week Range:  ${low_52w:.2f} — ${high_52w:.2f}")
print(f"Price Position: {price_position:.0f}% of 52-week range")
print()
print("--- MOVING AVERAGES ---")
print(f"SMA20:  ${sma_20:.2f}")
print(f"SMA50:  ${sma_50:.2f}")
print(f"SMA200: ${sma_200:.2f}")
print()
print("--- MOMENTUM ---")
print(f"RSI(14):   {rsi:.1f}")
print(f"MACD:      {macd_val:.3f}")
print(f"Signal:    {signal_val:.3f}")
print(f"Histogram: {macd_h_val:.3f}")
print()
print("--- PERFORMANCE ---")
print(f"1-Week:  {week_change:+.2f}%")
print(f"1-Month: {month_change:+.2f}%")
print()
print("--- SIGNAL ANALYSIS ---")
for s in signals:
    print(f" • {s}")
print()
print(f"{'='*60}")
print(f"TRADING SIGNAL: {signal}")
print(f"Score: {score:+d} / ~±7")
print(f"{'='*60}")
print()
print("--- DISCLAIMER ---")
print("This is for informational purposes only, not financial advice.")
print("Past performance does not guarantee future results.")
print("Do your own due diligence before making investment decisions.")
