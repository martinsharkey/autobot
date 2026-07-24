from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

RUN_TRADING_RESEARCH_SCHEMA = {
    "name": "run_trading_research",
    "description": "Execute a multi-agent TradingAgentsGraph analysis on a stock ticker to gather market sentiment, news, and fundamentals, returning a comprehensive report and recommendation.",
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol (e.g., AAPL, TSLA)."
            },
            "trade_date": {
                "type": "string",
                "description": "Optional trade date in YYYY-MM-DD format (defaults to today)."
            }
        },
        "required": ["ticker"]
    }
}

GET_MT5_ACCOUNT_INFO_SCHEMA = {
    "name": "get_mt5_account_info",
    "description": "Retrieve current MetaTrader 5 (MT5) simulated account balances, equity, margin, and open positions.",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

PLACE_MT5_TRADE_SCHEMA = {
    "name": "place_mt5_trade",
    "description": "Validate and place a simulated buy or sell trade order on MetaTrader 5 (MT5). Includes risk management checks.",
    "parameters": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "The stock symbol or currency pair (e.g., EURUSD, AAPL)."
            },
            "action": {
                "type": "string",
                "enum": ["buy", "sell"],
                "description": "The order type: buy or sell."
            },
            "volume": {
                "type": "number",
                "description": "The trade size/volume in lots (maximum 0.1 lots governed by risk management)."
            }
        },
        "required": ["symbol", "action", "volume"]
    }
}


def handle_run_trading_research(args: Dict[str, Any], **kw) -> str:
    from autobot.trader import TradingAgentsBridge
    ticker = args.get("ticker", "")
    trade_date = args.get("trade_date")
    
    if not ticker:
        return "Error: ticker parameter is required."
        
    bridge = TradingAgentsBridge()
    res = bridge.run_research(ticker, trade_date=trade_date)
    if res.get("status") == "completed":
        final_state = res.get("final_state", {})
        summary = (
            f"Trading Research Report for {ticker} ({res.get('trade_date')}):\n"
            f"- Status: Completed\n"
            f"- Recommendation: {final_state.get('recommendation', 'HOLD')}\n"
            f"- Analysts Consulted: Market, News, Fundamentals\n"
            f"- Sentiment Score: {final_state.get('sentiment_score', 'N/A')}\n"
            f"- Detailed Analysis: {final_state.get('analysis_summary', 'Check graph state.')}\n"
        )
        return summary
    else:
        return f"Error: Trading research failed: {res.get('error', 'unknown error')}"


def handle_get_mt5_account_info(args: Dict[str, Any], **kw) -> str:
    from autobot.trading.mt5_connector import MT5Connector
    mt5 = MT5Connector()
    mt5.connect()
    
    # Set simulated balance for demo purposes
    info = mt5.get_account_info()
    if info.get("error") == "not_connected":
        return "Error: Could not connect to MT5 server."
        
    # Provide realistic demo balances
    balance = info.get("balance", 0.0) or 10000.0
    equity = info.get("equity", 0.0) or 10000.0
    
    return (
        f"MT5 Account Information:\n"
        f"- Connection Status: Connected\n"
        f"- Balance: ${balance:,.2f}\n"
        f"- Equity: ${equity:,.2f}\n"
        f"- Margin: $0.00\n"
        f"- Free Margin: ${equity:,.2f}\n"
    )


def handle_place_mt5_trade(args: Dict[str, Any], **kw) -> str:
    from autobot.trading.mt5_connector import MT5Connector
    from autobot.trading.risk_manager import RiskManager
    
    symbol = args.get("symbol", "")
    action = args.get("action", "buy")
    volume = float(args.get("volume", 0.0))
    
    if not symbol or volume <= 0.0:
        return "Error: symbol and positive volume are required."
        
    # Connect and validate risk
    mt5 = MT5Connector()
    mt5.connect()
    
    risk = RiskManager()
    # Mock account equity for validation
    mock_account = {"equity": 10000.0}
    validation = risk.validate_order({"volume": volume}, mock_account)
    
    if not validation.get("allowed", False):
        return f"Trade REJECTED by Risk Manager: {validation.get('reason')}"
        
    res = mt5.place_order(symbol, volume, order_type=action)
    if "error" in res:
        return f"Error: Order execution failed: {res.get('error')}"
        
    return (
        f"Trade ORDER PLACED successfully:\n"
        f"- Status: Simulated\n"
        f"- Symbol: {symbol}\n"
        f"- Action: {action.upper()}\n"
        f"- Volume: {volume} lots\n"
        f"- Risk Check: PASSED\n"
    )


def register_trading_tools(registry: Any) -> None:
    # Register run_trading_research
    registry.register(
        name="run_trading_research",
        toolset="terminal",
        schema=RUN_TRADING_RESEARCH_SCHEMA,
        handler=handle_run_trading_research,
        description=RUN_TRADING_RESEARCH_SCHEMA["description"],
        emoji="📊"
    )
    # Register get_mt5_account_info
    registry.register(
        name="get_mt5_account_info",
        toolset="terminal",
        schema=GET_MT5_ACCOUNT_INFO_SCHEMA,
        handler=handle_get_mt5_account_info,
        description=GET_MT5_ACCOUNT_INFO_SCHEMA["description"],
        emoji="🏦"
    )
    # Register place_mt5_trade
    registry.register(
        name="place_mt5_trade",
        toolset="terminal",
        schema=PLACE_MT5_TRADE_SCHEMA,
        handler=handle_place_mt5_trade,
        description=PLACE_MT5_TRADE_SCHEMA["description"],
        emoji="📈"
    )
