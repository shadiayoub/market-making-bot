# Market Making Bot for LBank

A market-making bot that interacts with the LBank exchange API to provide liquidity for trading pairs. The bot places buy and sell orders at strategic price levels, adjusting for market volatility to profit from the spread.

## Features

- **Automated Market Making**: Places multiple buy and sell orders around market price
- **Dynamic Order Sizing**: Adjusts order sizes based on available balance and market volatility
- **Order Distance Range**: Configurable from 0.25% to 10% from market price
- **Balance Management**: Uses 95% of USDT and 90% of tokens (leaves buffers for fees)
- **Order Validation**: Ensures minimum order value (5 USDT) and size requirements
- **Maker Orders**: Uses limit orders to avoid trading fees
- **Docker Support**: Easy deployment with Docker Compose
- **Environment Variables**: Secure credential management via `.env` file

## Project Structure

```
market-making-bot/
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker Compose configuration
├── .env.example           # Environment variables template
├── src/
│   ├── market_making.py   # Core market-making strategy
│   └── utils.py           # API utilities and helper functions
└── README.md              # This file
```

## Prerequisites

- Python 3.8+ (for local development)
- Docker and Docker Compose (for containerized deployment)
- LBank account with API access enabled
- Sufficient balance: USDT for buy orders, tokens for sell orders

## Quick Start with Docker (Recommended)

1. **Clone the repository:**
   ```sh
   git clone <repository-url>
   cd market-making-bot
   ```

2. **Set up environment variables:**
   ```sh
   cp .env.example .env
   # Edit .env with your LBank API credentials and trading pair
   ```

3. **Start the bot:**
   ```sh
   docker-compose up -d
   ```

4. **View logs:**
   ```sh
   docker logs -f lbank-market-making-bot
   ```

5. **Stop the bot:**
   ```sh
   docker-compose down
   ```

## Local Development Setup

### Installation

1. **Create and activate virtual environment:**
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```sh
   cp .env.example .env
   # Edit .env with your credentials
   ```

### Configuration

The bot uses environment variables for configuration. Create a `.env` file with:

```env
# LBank API Credentials
LBANK_API_KEY=your_api_key_here
LBANK_API_SECRET=your_api_secret_here
LBANK_SIGN_METHOD=HMACSHA256  # or "RSA"
LBANK_BASE_URL=https://api.lbkex.com/

# Trading Pair Configuration
TRADING_PAIR=acces_usdt
TOKEN_SYMBOL=acces
```

**Important Notes:**
- **Sign Method**: Use `HMACSHA256` if your `api_secret` is a hex string (recommended). Use `RSA` only if you have an RSA private key.
- **Trading Pair**: Format should be `token_usdt` (lowercase with underscore)
- **Base URL**: Usually `https://api.lbkex.com/` for production

### Running the Bot

```sh
python main.py
```

Stop the bot with `Ctrl+C` (orders will be automatically cancelled).

## Configuration Parameters

Edit `main.py` to customize bot behavior:

```python
market_making(
    max_order_size=10000,      # Maximum order size in tokens
    min_order_size=10,         # Minimum order size in tokens
    num_orders=20,             # Number of positions per side
    base_price_step_percentage=0.0025,  # Base step: 0.25% (range: 0.25% - 10%)
)
```

### Parameter Guidelines

- **Total Amount**: Designed for ~500 USDT total allocation
- **Number of Positions**: 20 positions per side (buy + sell)
- **Order Distance**: 0.25% to 10% from market price
- **Order Distribution**: 
  - First order: ~30% of total size
  - Remaining orders: Decreasing sizes
- **Price Steps**:
  - Orders 0-8: Base step (0.25%)
  - Orders 9-11: 2.5x base step
  - Orders 12+: 4x base step

## How It Works

1. **Market Data Fetching**: Retrieves order book, account balance, and market volatility
2. **Order Calculation**: 
   - Calculates order sizes based on available balance and volatility
   - Distributes orders across price levels (0.25% to 10% from market)
   - Validates minimum order value (5 USDT) and size requirements
3. **Order Placement**:
   - Cancels existing orders before placing new ones
   - Places maker orders (limit orders) to avoid fees
   - Tracks order IDs for efficient management
4. **Risk Management**:
   - Uses 95% of USDT and 90% of tokens (leaves buffers)
   - Adjusts order sizes based on market volatility
   - Validates orders meet exchange minimums before placement

## Safety Features (Planned)

The following safety features are planned for future implementation:

- ✅ **Spread Validation**: Skip trading if spread > 30% (illiquid market protection)
- ✅ **Maximum Loss Limit**: Stop bot if loss exceeds 20% of initial balance
- ✅ **Position Size Cap**: Limit total exposure to 80% of balance
- ✅ **Dynamic Distance Adjustment**: Reduce max distance to 5% when spread > 20%

*Note: These features are tracked in the project TODO list and will be implemented in future updates.*

## Monitoring

### Docker Logs

```sh
# Follow logs in real-time
docker logs -f lbank-market-making-bot

# View last 100 lines
docker logs --tail 100 lbank-market-making-bot
```

### Log Output Format

The bot provides detailed logging:
- `[INIT]`: Initialization and balance checks
- `[MARKET]`: Market data (bid, ask, spread)
- `[CALC]`: Order size and volatility calculations
- `[ORDERS]`: Order placement and cancellation status
- `[BUY/SELL #N]`: Individual order details
- `[SUMMARY]`: Iteration summary with success/failure counts

## Troubleshooting

### Common Issues

1. **"currency pair nonsupport"**
   - Verify trading pair format in `.env` (should be lowercase with underscore)
   - Some pairs may not support API trading (view-only)

2. **"Wrong signature method"**
   - Ensure `LBANK_SIGN_METHOD` matches your API secret type
   - Use `HMACSHA256` for hex string secrets (recommended)

3. **"Currency is not enough"**
   - Check account balance
   - Bot uses 95% of USDT and 90% of tokens (leaves buffers)

4. **"The order price or order quantity must be greater than the minimum value"**
   - Bot validates minimum 5 USDT per order
   - Increase balance or reduce `num_orders` if needed

5. **Docker container exits immediately**
   - Check logs: `docker logs lbank-market-making-bot`
   - Verify `.env` file exists and has correct credentials

## API Documentation

For detailed LBank API documentation, see `Trading-REST-API.md` in this repository.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## Disclaimer

**⚠️ WARNING: Trading cryptocurrencies involves substantial risk of loss.**

This bot is for educational purposes only. Use it at your own risk. The developers are not responsible for any financial losses. Always:
- Test with small amounts first
- Monitor the bot regularly
- Understand the risks involved
- Never invest more than you can afford to lose

## License

This project is licensed under the MIT License.
