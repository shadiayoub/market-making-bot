import traceback
import os
from dotenv import load_dotenv
from src.market_making import market_making

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    try:
        # Parameters for market making bot:
        # - Total amount: 500 USDT
        # - Number of positions: 20
        # - Order distance: 0.25% - 10% from market price
        # 
        # Order size calculation:
        # - Average per position: 500 USDT / 20 = 25 USDT
        # - First order (30%): ~150 USDT worth
        # - Remaining orders: ~350 USDT total
        # Note: max_order_size and min_order_size are in token amounts
        # The function will adjust based on available balance and current price
        
        # Set max_order_size to allow for ~150-200 USDT per order (adjust based on token price)
        # Set min_order_size to ensure orders aren't too small
        # Note: With 104.50 USDT, we can buy ~145 tokens at 0.2475, so min_order_size of 100
        # means we can only place 1 order. Lowering to allow more orders.
        
        # LBank Compliance Mode: Concentrates 500-1000 USDT within ±1% of market price
        # Enable this when you have sufficient balance (500+ USDT) to meet LBank market making requirements
        ENABLE_COMPLIANCE_MODE = os.getenv("ENABLE_COMPLIANCE_MODE", "true").lower() == "true"
        
        # Read safety features from environment variables with defaults
        MAX_SPREAD_PCT = float(os.getenv("MAX_SPREAD_PCT", "30.0"))
        MAX_LOSS_PCT = float(os.getenv("MAX_LOSS_PCT", "20.0"))
        MAX_EXPOSURE_PCT = float(os.getenv("MAX_EXPOSURE_PCT", "80.0"))
        REDUCE_DISTANCE_ON_WIDE_SPREAD = os.getenv("REDUCE_DISTANCE_ON_WIDE_SPREAD", "true").lower() == "true"
        WIDE_SPREAD_THRESHOLD = float(os.getenv("WIDE_SPREAD_THRESHOLD", "20.0"))
        
        # Read adaptive pricing from environment variables
        ENABLE_ADAPTIVE_PRICING = os.getenv("ENABLE_ADAPTIVE_PRICING", "true").lower() == "true"
        TIGHTENING_RATE = float(os.getenv("TIGHTENING_RATE", "0.001"))
        TIGHTENING_TRIGGER = int(os.getenv("TIGHTENING_TRIGGER", "2"))
        
        # Read max buy price from environment (optional - set to 0 or empty to disable)
        MAX_BUY_PRICE_STR = os.getenv("MAX_BUY_PRICE", "").strip()
        MAX_BUY_PRICE = float(MAX_BUY_PRICE_STR) if MAX_BUY_PRICE_STR and float(MAX_BUY_PRICE_STR) > 0 else None
        
        market_making(
            max_order_size=10000,  # Maximum order size in tokens (will be capped by available balance)
            min_order_size=10,     # Minimum order size in tokens (lowered to allow more orders with limited balance)
            num_orders=20,         # Number of positions (used in standard mode, limited to ±1% in compliance mode)
            base_price_step_percentage=0.0025,  # Base step: 0.25% (orders will range from 0.25% to 10% in standard mode)
            compliance_mode=ENABLE_COMPLIANCE_MODE,  # Enable LBank compliance mode
            compliance_min_usdt=500,  # Minimum USDT within ±1% (LBank requirement)
            compliance_max_usdt=1000,  # Maximum USDT within ±1% (LBank requirement)
            enable_adaptive_pricing=ENABLE_ADAPTIVE_PRICING,  # Gradually move prices closer to market if orders don't fill
            tightening_rate=TIGHTENING_RATE,  # Move closer per iteration after trigger
            tightening_trigger=TIGHTENING_TRIGGER,  # Start tightening after N unfilled iterations
            # Safety features (from environment variables)
            max_spread_pct=MAX_SPREAD_PCT,  # Skip trading if spread exceeds this
            max_loss_pct=MAX_LOSS_PCT,  # Stop bot if loss exceeds this
            max_exposure_pct=MAX_EXPOSURE_PCT,  # Limit total exposure to this % of balance
            reduce_distance_on_wide_spread=REDUCE_DISTANCE_ON_WIDE_SPREAD,  # Reduce max distance when spread is wide
            wide_spread_threshold=WIDE_SPREAD_THRESHOLD,  # Spread threshold for distance reduction
            max_buy_price=MAX_BUY_PRICE,  # Maximum buy price limit (None to disable)
        )

    except KeyboardInterrupt:
        print("Main process interrupted")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
