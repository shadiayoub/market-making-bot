import traceback
from src.market_making import market_making

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
        ENABLE_COMPLIANCE_MODE = True  # Set to False for standard mode (0.25% - 10% range)
        
        market_making(
            max_order_size=10000,  # Maximum order size in tokens (will be capped by available balance)
            min_order_size=10,     # Minimum order size in tokens (lowered to allow more orders with limited balance)
            num_orders=20,         # Number of positions (used in standard mode, limited to ±1% in compliance mode)
            base_price_step_percentage=0.0025,  # Base step: 0.25% (orders will range from 0.25% to 10% in standard mode)
            compliance_mode=ENABLE_COMPLIANCE_MODE,  # Enable LBank compliance mode
            compliance_min_usdt=500,  # Minimum USDT within ±1% (LBank requirement)
            compliance_max_usdt=1000,  # Maximum USDT within ±1% (LBank requirement)
        )

    except KeyboardInterrupt:
        print("Main process interrupted")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
