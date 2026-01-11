# Market Making Bot Configuration Guide

## Summary of Changes

The bot has been configured with the following parameters:
- **Total amount**: 500 USDT
- **Number of positions**: 20
- **Order distance range**: 0.25% - 10% from market price

## Parameters Configured

### Order Sizes
- `max_order_size`: 10000 tokens (maximum per order, will be capped by available balance)
- `min_order_size`: 100 tokens (minimum per order)
- **Note**: These are in token amounts. The function automatically adjusts based on:
  - Available balance (USDT for buys, tokens for sells)
  - Current token price
  - Market volatility

### Trading Parameters
- `num_orders`: 20 positions (10 buy + 10 sell orders)
- `base_price_step_percentage`: 0.0025 (0.25% base step)
- Orders are distributed from 0.25% to 10% away from market price

### Price Distribution
- Order 0: At market price (within spread)
- Orders 1-19: Distributed from 0.25% to 10% away
- Buy orders: Below market price (decreasing)
- Sell orders: Above market price (increasing)

## Required Configuration Before Starting

### 1. API Credentials (src/utils.py)
Update the following with your LBank API credentials:
```python
client = BlockHttpClient(
    sign_method="HMACSHA256",  # Use "HMACSHA256" for secret key strings, or "RSA" for RSA private keys
    api_key="YOUR_API_KEY",  # Replace with your API key
    api_secret="YOUR_API_SECRET",  # Replace with your API secret (hex string for HMACSHA256, or RSA private key for RSA)
    base_url="https://www.lbkex.net/",
    log_level=logging.ERROR,
)
```

**Note on Sign Methods:**
- **HMACSHA256**: Use this if your `api_secret` is a hex string (most common). This is simpler and recommended.
- **RSA**: Use this only if you have an RSA private key from LBank. The key must be in PEM format (without BEGIN/END headers in the api_secret field).

### 2. Trading Pair (src/utils.py)
Update the trading pair and token symbol:
```python
pair = "acces_usdt"  # Replace with your trading pair (e.g., "btc_usdt")
token_symbol = "acces"  # Replace with your token symbol (e.g., "btc")
```

**Important**: The `SYMBOL` in `market_making.py` now automatically uses the `pair` from `utils.py`, so you only need to update it in one place.

### 3. Account Balance
Ensure you have sufficient balance:
- **USDT**: At least 500 USDT for buy orders
- **Token**: Sufficient tokens for sell orders (equivalent to ~500 USDT worth)

### 4. Order Size Adjustment (Optional)
If your token price is significantly different, you may need to adjust `max_order_size` and `min_order_size` in `main.py`:
- For higher-priced tokens: Reduce these values
- For lower-priced tokens: Increase these values
- The function will automatically cap based on available balance

## How It Works

1. **Order Distribution**: Orders are distributed unevenly:
   - First order: ~30% of total size
   - Remaining orders: Decreasing sizes

2. **Price Steps**: 
   - Orders 0-8: Use base step (0.25%)
   - Orders 9-11: Use 2.5x base step
   - Orders 12+: Use 4x base step
   - This ensures coverage from 0.25% to 10%

3. **Risk Management**:
   - Pauses trading if balance drops >10%
   - Resumes when balance recovers to >-1%
   - Adjusts order sizes based on volatility

4. **Order Management**:
   - Cancels existing orders before placing new ones
   - Tracks order IDs for efficient cancellation
   - Places maker orders (limit orders)

## Starting the Bot

1. Ensure all configuration is complete (API keys, trading pair)
2. Activate virtual environment: `source venv/bin/activate`
3. Run: `python main.py`
4. Monitor the output for order placements
5. Stop with `Ctrl+C` (orders will be cancelled)

## Notes

- The bot uses maker orders to avoid trading fees
- Order sizes are automatically adjusted based on available balance
- The bot adapts to market volatility
- Ensure you have sufficient balance for both buy and sell sides
