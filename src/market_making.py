import time
import traceback
from src.utils import (
    place_order,
    cancel_all_orders,
    cancel_list_of_orders,
    calculate_order_size,
    get_dynamic_sleep_time,
    get_dynamic_volatilit,
    calculate_order_sizes,
    get_price_step_percentage,
    fetch_account_balance,
    calculate_percentage_change,
    get_num_of_orders,
    get_order_book,
    get_buy_price_in_spread,
    get_sell_price_in_spread,
    pair,
    token_symbol,
)

buy_order_ids = []
sell_order_ids = []
SYMBOL = pair  # Use the pair from utils.py

# Track iterations for adaptive pricing (gradual spread narrowing)
unfilled_iterations = 0  # Count of iterations with unfilled orders


def market_making(
    max_order_size,
    min_order_size,
    num_orders=20,
    base_price_step_percentage=0.0025,
    compliance_mode=False,
    compliance_min_usdt=500,
    compliance_max_usdt=1000,
    enable_adaptive_pricing=True,
    tightening_rate=0.001,  # Move 0.1% closer per iteration
    tightening_trigger=2,  # Start tightening after 2 unfilled iterations
    # Safety features
    max_spread_pct=30.0,  # Skip trading if spread > 30%
    max_loss_pct=20.0,  # Stop bot if loss > 20%
    max_exposure_pct=80.0,  # Limit total exposure to 80% of balance
    reduce_distance_on_wide_spread=True,  # Reduce max distance when spread > 20%
    wide_spread_threshold=20.0,  # Spread threshold for distance reduction
):
    global SYMBOL, unfilled_iterations  # Declare global at function level
    
    print("=" * 60)
    print("Market Making Bot Starting...")
    print(f"Trading Pair: {SYMBOL}")
    print(f"Token Symbol: {token_symbol}")
    if compliance_mode:
        print(f"Compliance Mode: ENABLED (LBank requirement: {compliance_min_usdt}-{compliance_max_usdt} USDT within ±1%)")
        print(f"Number of Positions: Concentrated within ±1% range")
    else:
        print(f"Number of Positions: {num_orders} (per side)")
        print(f"Order Distance Range: 0.25% - 10% from market price")
        print(f"Max Order Size: {max_order_size} tokens")
        print(f"Min Order Size: {min_order_size} tokens")
        print(f"Safety Features:")
        print(f"  - Max Spread: {max_spread_pct}% (skip if exceeded)")
        print(f"  - Max Loss: {max_loss_pct}% (stop if exceeded)")
        print(f"  - Max Exposure: {max_exposure_pct}% of balance")
        print(f"  - Wide Spread Protection: {'Enabled' if reduce_distance_on_wide_spread else 'Disabled'}")
        print("=" * 60)
    
    try:
        print("\n[INIT] Fetching initial account balance...")
        initial_balance = fetch_account_balance()
        initial_usdt_balance = (
            initial_balance["usdt"]["free"] + initial_balance["usdt"]["locked"]
        )
        initial_token_balance = (
            initial_balance[token_symbol]["free"] + initial_balance[token_symbol]["locked"]
        )
        
        # Calculate initial total balance in USDT for loss tracking
        # We'll need current price to convert tokens to USDT
        try:
            initial_order_book = get_order_book(SYMBOL)
            if initial_order_book and initial_order_book.get("result") in ["true", True]:
                initial_data = initial_order_book.get("data", {})
                initial_bid = float(initial_data.get("bidPrice", 0))
                initial_ask = float(initial_data.get("askPrice", 0))
                if initial_bid > 0 and initial_ask > 0:
                    initial_mid_price = (initial_bid + initial_ask) / 2
                    initial_total_balance_usdt = initial_usdt_balance + (initial_token_balance * initial_mid_price)
                else:
                    initial_total_balance_usdt = initial_usdt_balance  # Fallback
            else:
                initial_total_balance_usdt = initial_usdt_balance  # Fallback
        except:
            initial_total_balance_usdt = initial_usdt_balance  # Fallback if price fetch fails
        
        print(f"[INIT] Initial USDT Balance: {initial_usdt_balance:.2f} USDT")
        print(f"[INIT] Initial {token_symbol.upper()} Balance: {initial_token_balance:.2f} {token_symbol.upper()}")
        print(f"[INIT] Initial Total Balance: {initial_total_balance_usdt:.2f} USDT")
        print("\n[INFO] Bot is now running. Press Ctrl+C to stop.\n")

        iteration = 0
        while True:
            iteration += 1
            try:
                print(f"\n[ITERATION {iteration}] Fetching market data...")
                order_book = get_order_book(SYMBOL)
                
                # Validate order book response
                if not order_book:
                    print("[WARNING] Failed to get order book, skipping this iteration")
                    time.sleep(get_dynamic_sleep_time(0.01))
                    continue

                balance = fetch_account_balance()
                usdt_free = balance["usdt"]["free"]
                usdt_locked = balance["usdt"]["locked"]
                usdt_total = usdt_free + usdt_locked
                token_free = balance[token_symbol]["free"]
                token_locked = balance[token_symbol]["locked"]
                token_total = token_free + token_locked

                usdt_change = calculate_percentage_change(
                    initial_usdt_balance, usdt_total
                )
                token_change = calculate_percentage_change(
                    initial_token_balance, token_total
                )
                
                print(f"[BALANCE] USDT: {usdt_free:.2f} free, {usdt_locked:.2f} locked, {usdt_total:.2f} total (Change: {usdt_change:+.2f}%)")
                print(f"[BALANCE] {token_symbol.upper()}: {token_free:.2f} free, {token_locked:.2f} locked, {token_total:.2f} total (Change: {token_change:+.2f}%)")
                
                # Warn if USDT is decreasing significantly
                if usdt_change < -1.0:  # More than 1% decrease
                    print(f"[WARNING] ⚠ USDT balance decreased by {abs(usdt_change):.2f}% - check if buy orders are filling without matching sells")

                # Initialize pause flags
                usdt_pause = False
                token_pause = False

                # Check if changes exceed the pause thresholds
                if usdt_change < -10:
                    usdt_pause = True
                if token_change < -10:
                    token_pause = True

                # Check if changes have recovered
                if usdt_change > -1:
                    usdt_pause = False
                if token_change > -1:
                    token_pause = False

                # Check if order book response is valid
                result = order_book.get("result")
                if result == "true" or result is True:
                    # Example of data: {'symbol': 'safi_usdt', 'askPrice': '0.055', 'askQty': '78.43', 'bidQty': '724.1', 'bidPrice': '0.054761'
                    data = order_book.get("data", {})
                    if not data:
                        print("No data in order book response, skipping this iteration")
                        time.sleep(get_dynamic_sleep_time(0.01))
                        continue
                    
                    # Get the actual symbol format from the order book response
                    actual_symbol = data.get("symbol", SYMBOL)
                    # Order creation works with lowercase (acces_usdt), not uppercase
                    # Keep using the original symbol format (lowercase) for order placement
                    # Don't change SYMBOL - it's already correct
                    
                    # The price a buyer is willing to pay
                    bid_price = float(data.get("bidPrice", 0))
                    # The price a seller is willing to accept
                    ask_price = float(data.get("askPrice", 0))
                    
                    if bid_price == 0 or ask_price == 0:
                        print("[WARNING] Invalid bid/ask prices, skipping this iteration")
                        time.sleep(get_dynamic_sleep_time(0.01))
                        continue

                    spread_pct = ((ask_price - bid_price) / bid_price) * 100
                    print(f"[MARKET] Bid: {bid_price:.6f} | Ask: {ask_price:.6f} | Spread: {spread_pct:.3f}%")
                    
                    # SAFETY FEATURE 1: Spread validation - skip trading if spread too wide
                    # BUT: In wide spreads, we can still trade to help narrow it (market making mode)
                    if spread_pct > max_spread_pct:
                        print(f"[SAFETY] ⚠ Spread very wide ({spread_pct:.2f}% > {max_spread_pct}%)")
                        print(f"[SAFETY] Continuing to trade to help narrow spread (market making mode)")
                        # Don't skip - continue trading to provide liquidity and narrow spread

                    # Calculate market volatility
                    print("[CALC] Calculating market volatility...")
                    current_volatility = get_dynamic_volatilit(60)
                    print(f"[CALC] Current Volatility: {current_volatility:.4f}")

                    # Dynamic Spread: More sophisticated and responsive strategy that adapts to market volatility.
                    # spread = calculate_dynamic_spread(current_volatility)
                    spread = 0.01
                    base_buy_price = bid_price * (1 - spread)
                    base_sell_price = ask_price * (1 + spread)
                    print(f"[PRICE] Base Buy Price: {base_buy_price:.6f} | Base Sell Price: {base_sell_price:.6f}")

                    # Check if there are existing orders BEFORE cancelling (for adaptive pricing tracking)
                    print("[ORDERS] Checking existing orders...")
                    current_orders_number = get_num_of_orders(SYMBOL)
                    print(f"[ORDERS] Found {current_orders_number} existing orders")
                    
                    # Check order status to detect filled orders BEFORE cancelling
                    filled_buy_value = 0.0
                    filled_sell_value = 0.0
                    filled_buy_qty = 0.0
                    filled_sell_qty = 0.0
                    cancelled_orders = 0
                    
                    if current_orders_number > 0:
                        try:
                            orders_response = get_current_orders(SYMBOL)
                            if orders_response and (orders_response.get("result") == "true" or orders_response.get("result") is True):
                                data = orders_response.get("data", {})
                                orders = data.get("orders", []) if isinstance(data, dict) else []
                                
                                for order in orders:
                                    if isinstance(order, dict):
                                        executed_qty = float(order.get("executedQty", 0) or 0)
                                        orig_qty = float(order.get("origQty", 0) or 0)
                                        price = float(order.get("price", 0) or 0)
                                        trade_type = order.get("tradeType", "").lower()
                                        status = order.get("status", 0)
                                        
                                        # Check if order was filled (executedQty > 0 or status indicates fill)
                                        if executed_qty > 0:
                                            if "buy" in trade_type:
                                                filled_buy_qty += executed_qty
                                                filled_buy_value += executed_qty * price
                                            elif "sell" in trade_type:
                                                filled_sell_qty += executed_qty
                                                filled_sell_value += executed_qty * price
                                        elif orig_qty > 0:
                                            # Order exists but not filled - will be cancelled
                                            cancelled_orders += 1
                            
                            if filled_buy_qty > 0 or filled_sell_qty > 0:
                                print(f"[FILLED] ⚠ Orders filled this iteration:")
                                if filled_buy_qty > 0:
                                    print(f"[FILLED]   Buy: {filled_buy_qty:.2f} tokens (~{filled_buy_value:.2f} USDT)")
                                if filled_sell_qty > 0:
                                    print(f"[FILLED]   Sell: {filled_sell_qty:.2f} tokens (~{filled_sell_value:.2f} USDT)")
                                print(f"[FILLED]   Net USDT change: {filled_sell_value - filled_buy_value:.2f} USDT")
                        except Exception as e:
                            print(f"[WARNING] Could not check order fill status: {e}")
                    
                    # Track unfilled orders for adaptive pricing BEFORE cancelling
                    if enable_adaptive_pricing:
                        if current_orders_number > 0 and cancelled_orders > 0:
                            unfilled_iterations += 1
                            print(f"[ADAPTIVE] Unfilled orders detected, iteration count: {unfilled_iterations}")
                        else:
                            # Orders filled or no orders - reset counter
                            if unfilled_iterations > 0:
                                print(f"[ADAPTIVE] Orders filled or none exist, resetting tightening counter")
                            unfilled_iterations = 0
                    
                    # Always cancel all orders to start fresh each iteration
                    # This prevents order accumulation and ensures clean state
                    if current_orders_number > 0:
                        print("[CANCEL] Cancelling all existing orders to start fresh...")
                        cancel_all_orders(SYMBOL)
                        sell_order_ids.clear()
                        buy_order_ids.clear()
                        if cancelled_orders > 0:
                            print(f"[CANCEL] Cancelled {cancelled_orders} unfilled orders")
                        print("[CANCEL] All orders cancelled")

                    # best_prices = get_best_price()
                    # best_sell_price = best_prices["best_sell"]
                    # best_buy_price = best_prices["best_buy"]
                    # best_sell_price = base_sell_price

                    # Get the best prices for selling and buying for a low market
                    base_best_buy_price = get_buy_price_in_spread()  # This should already be below bid
                    base_best_sell_price = get_sell_price_in_spread()
                    
                    # CRITICAL: Ensure buy price NEVER exceeds bid price
                    # Buy orders must be below bid to be maker orders and not push price up
                    if base_best_buy_price > bid_price:
                        print(f"[WARNING] base_best_buy_price ({base_best_buy_price:.6f}) exceeds bid ({bid_price:.6f}), capping at bid")
                        base_best_buy_price = bid_price * 0.999
                    
                    # Validate sell price is above ask price (critical for sell orders)
                    if base_best_sell_price <= 0 or base_best_sell_price < ask_price:
                        print(f"[WARNING] best_sell_price ({base_best_sell_price:.6f}) is invalid or below ask ({ask_price:.6f}), recalculating")
                        base_best_sell_price = ask_price * 1.02
                    
                    # ADAPTIVE PRICING: Gradually move sell prices down toward bid to drive price down
                    # Buy orders: Never place higher than current bid
                    # Sell orders: Gradually move down from ask toward bid
                    if enable_adaptive_pricing:
                        # BUY ORDERS: Never place higher than current bid (to avoid pushing price up)
                        # Use bid price as maximum, or slightly below for safety
                        best_buy_price = min(bid_price * 0.999, base_best_buy_price)  # At or below bid
                        
                        # Double-check: ensure it's never above bid
                        if best_buy_price > bid_price:
                            print(f"[ERROR] best_buy_price ({best_buy_price:.6f}) exceeds bid ({bid_price:.6f}), forcing to bid * 0.999")
                            best_buy_price = bid_price * 0.999
                        
                        # SELL ORDERS: Gradually move down from ask toward bid
                        # Calculate how far to move down based on iterations
                        is_wide_spread = spread_pct > wide_spread_threshold
                        
                        if is_wide_spread:
                            # In wide spreads, move more aggressively
                            # Calculate progress toward bid (0 = at ask, 1 = at bid)
                            # Start moving immediately in wide spreads (unfilled_iterations already tracked above)
                            progress_toward_bid = min(
                                (unfilled_iterations + 1) * tightening_rate * 10,  # Move faster in wide spreads
                                1.0  # Maximum: reach bid
                            )
                        else:
                            # Normal spreads: wait for trigger, then move gradually
                            if unfilled_iterations >= tightening_trigger:
                                progress_toward_bid = min(
                                    (unfilled_iterations - tightening_trigger + 1) * tightening_rate * 5,
                                    1.0
                                )
                            else:
                                progress_toward_bid = 0.0
                        
                        # Calculate sell price: start at ask, move toward bid
                        price_range = ask_price - bid_price
                        target_sell_price = ask_price - (price_range * progress_toward_bid)
                        
                        # Strategy: Start above ask, then gradually move down
                        # Phase 1: Stay above ask (progress 0-10%) - provide liquidity above market
                        # Phase 2: Move toward ask (progress 10-50%) - narrow the gap
                        # Phase 3: Move toward bid (progress 50-100%) - drive price down
                        
                        if progress_toward_bid < 0.10:  # First 10%: Stay above ask
                            # Start at ask + premium, gradually reduce premium
                            premium = 0.02 * (1 - progress_toward_bid / 0.10)  # 2% down to 0% premium
                            best_sell_price = ask_price * (1 + premium)
                        elif progress_toward_bid < 0.50:  # 10-50%: Move from ask toward mid
                            # Move from ask toward mid-price
                            mid_progress = (progress_toward_bid - 0.10) / 0.40  # 0 to 1 within this phase
                            mid_price = (bid_price + ask_price) / 2
                            best_sell_price = ask_price - ((ask_price - mid_price) * mid_progress)
                        else:  # 50-100%: Move from mid toward bid
                            # Move from mid-price toward bid
                            bid_progress = (progress_toward_bid - 0.50) / 0.50  # 0 to 1 within this phase
                            mid_price = (bid_price + ask_price) / 2
                            best_sell_price = mid_price - ((mid_price - bid_price) * bid_progress)
                        
                        # Safety: Ensure sell price is always above bid
                        if best_sell_price <= bid_price:
                            best_sell_price = bid_price * 1.001  # Minimum 0.1% above bid
                        
                        if is_wide_spread or (unfilled_iterations >= tightening_trigger and progress_toward_bid > 0):
                            print(f"[ADAPTIVE] Driving price down (unfilled iterations: {unfilled_iterations}):")
                            print(f"[ADAPTIVE]   Buy: Capped at bid {bid_price:.6f} (using {best_buy_price:.6f})")
                            print(f"[ADAPTIVE]   Sell: Progress {progress_toward_bid*100:.2f}% toward bid")
                            print(f"[ADAPTIVE]   Sell: {base_best_sell_price:.6f} → {best_sell_price:.6f} (target: {bid_price:.6f}, ask: {ask_price:.6f})")
                        else:
                            # Use base prices initially
                            best_sell_price = base_best_sell_price
                            if unfilled_iterations > 0:
                                print(f"[ADAPTIVE] Waiting for {tightening_trigger - unfilled_iterations} more iteration(s) before moving sell prices down")
                    else:
                        # No adaptive pricing - use base prices
                        best_buy_price = base_best_buy_price
                        best_sell_price = base_best_sell_price
                        
                        # CRITICAL: Still ensure buy price doesn't exceed bid
                        if best_buy_price > bid_price:
                            print(f"[WARNING] best_buy_price ({best_buy_price:.6f}) exceeds bid ({bid_price:.6f}), capping at bid * 0.999")
                            best_buy_price = bid_price * 0.999
                    
                    print(f"[PRICE] Best Buy Price: {best_buy_price:.6f} | Best Sell Price: {best_sell_price:.6f} (Ask: {ask_price:.6f}, Bid: {bid_price:.6f})")

                    print("[CALC] Calculating order sizes...")
                    
                    # Get current balances for validation (BEFORE placing orders)
                    balance_before_orders = fetch_account_balance()
                    available_usdt = balance_before_orders["usdt"]["free"]
                    available_tokens = balance_before_orders[token_symbol]["free"]
                    usdt_locked_before = balance_before_orders["usdt"]["locked"]
                    token_locked_before = balance_before_orders[token_symbol]["locked"]
                    
                    # Track balance before placing orders for comparison
                    total_usdt_before = available_usdt + usdt_locked_before
                    total_tokens_before = available_tokens + token_locked_before
                    
                    current_balance = balance_before_orders
                    
                    # Calculate current total balance in USDT for loss tracking
                    mid_price = (bid_price + ask_price) / 2
                    current_total_balance_usdt = available_usdt + (available_tokens * mid_price)
                    
                    # SAFETY FEATURE 2: Maximum loss limit check
                    if initial_total_balance_usdt > 0:
                        loss_pct = ((initial_total_balance_usdt - current_total_balance_usdt) / initial_total_balance_usdt) * 100
                        if loss_pct > max_loss_pct:
                            print(f"[SAFETY] 🛑 MAXIMUM LOSS REACHED: {loss_pct:.2f}% loss exceeds {max_loss_pct}% limit")
                            print(f"[SAFETY] Initial Balance: {initial_total_balance_usdt:.2f} USDT")
                            print(f"[SAFETY] Current Balance: {current_total_balance_usdt:.2f} USDT")
                            print(f"[SAFETY] Stopping bot to prevent further losses...")
                            break  # Exit the main loop
                        elif loss_pct > max_loss_pct * 0.8:  # Warning at 80% of limit
                            print(f"[SAFETY] ⚠ Warning: Loss at {loss_pct:.2f}% (approaching {max_loss_pct}% limit)")
                    else:
                        loss_pct = 0.0
                    
                    # Calculate maximum tokens we can buy with available USDT
                    # Use 95% of available to leave buffer for fees and rounding
                    max_buy_tokens = (available_usdt * 0.95) / best_buy_price
                    
                    buy_total_order_size = calculate_order_size(
                        "buy",
                        current_volatility,
                        max_order_size,
                        min_order_size,
                    )
                    
                    # CRITICAL: Validate buy order size doesn't exceed available USDT
                    if buy_total_order_size > max_buy_tokens:
                        print(f"[WARNING] Buy order size ({buy_total_order_size:.2f}) exceeds available USDT. Limiting to {max_buy_tokens:.2f} tokens")
                        buy_total_order_size = max_buy_tokens
                    
                    # Double-check: ensure total doesn't exceed available
                    estimated_total_value = buy_total_order_size * best_buy_price
                    if estimated_total_value > available_usdt * 0.95:
                        buy_total_order_size = (available_usdt * 0.95) / best_buy_price
                        print(f"[WARNING] Adjusted buy total to {buy_total_order_size:.2f} tokens to match available USDT")
                    
                    # If total is less than minimum for one order, adjust minimum or skip
                    effective_min_buy = min_order_size
                    if buy_total_order_size < min_order_size:
                        if buy_total_order_size > 0:
                            print(f"[WARNING] Total buy size ({buy_total_order_size:.2f}) is below minimum per order ({min_order_size}). Using total as single order.")
                            effective_min_buy = buy_total_order_size * 0.5  # Allow smaller orders
                        else:
                            effective_min_buy = 0

                    # Calculate how many orders we can realistically place with available USDT
                    # Target: each order should be at least 5 USDT value
                    MIN_ORDER_VALUE = 5.0
                    min_tokens_per_order = MIN_ORDER_VALUE / best_buy_price
                    max_realistic_orders = min(
                        num_orders,
                        int((available_usdt * 0.95) / MIN_ORDER_VALUE),
                        int(buy_total_order_size / max(min_tokens_per_order, effective_min_buy))
                    )
                    
                    # If we can't place many orders, reduce the target to ensure quality
                    if max_realistic_orders < num_orders * 0.5:
                        # Create fewer, larger orders that will definitely meet minimums
                        target_orders = max(1, max_realistic_orders)
                        print(f"[INFO] Adjusting to {target_orders} buy orders to ensure all meet {MIN_ORDER_VALUE} USDT minimum")
                        buy_order_sizes = calculate_order_sizes(
                            buy_total_order_size, target_orders, max(min_tokens_per_order, effective_min_buy)
                        )
                    else:
                        buy_order_sizes = calculate_order_sizes(
                            buy_total_order_size, num_orders, effective_min_buy
                        )
                    
                    # Final safety check: ensure total value doesn't exceed available USDT
                    if len(buy_order_sizes) > 0:
                        total_buy_value_check = sum(size * best_buy_price for size in buy_order_sizes)
                        if total_buy_value_check > available_usdt * 0.95:
                            # Scale down all orders proportionally
                            scale_factor = (available_usdt * 0.95) / total_buy_value_check
                            buy_order_sizes = [size * scale_factor for size in buy_order_sizes]
                            print(f"[WARNING] Scaled down buy orders by {scale_factor:.3f} to fit available USDT")
                            
                            # After scaling, we'll filter based on order value in the validation step below
                            # Don't filter here - let the value-based check handle it

                    sell_total_order_size = calculate_order_size(
                        "sell",
                        current_volatility,
                        max_order_size,
                        min_order_size,
                    )
                    
                    # Validate sell order size doesn't exceed available tokens
                    max_sell_tokens = available_tokens * 0.90  # 90% of tokens, leave 10% buffer
                    if sell_total_order_size > max_sell_tokens:
                        print(f"[WARNING] Sell order size ({sell_total_order_size:.2f}) exceeds available tokens. Limiting to {max_sell_tokens:.2f} tokens")
                        sell_total_order_size = max_sell_tokens

                    sell_order_sizes = calculate_order_sizes(
                        sell_total_order_size, num_orders, min_order_size
                    )
                    
                    # Filter out zero-sized orders
                    buy_order_sizes = [s for s in buy_order_sizes if s > 0]
                    sell_order_sizes = [s for s in sell_order_sizes if s > 0]
                    
                    # For buy orders: filter based on minimum order value (5 USDT for safety) and minimum size
                    # Exchange seems to require higher minimums than 1 USDT
                    MIN_ORDER_VALUE = 5.0  # Minimum order value in USDT
                    filtered_buy_sizes = []
                    for size in buy_order_sizes:
                        order_value = size * best_buy_price
                        # Accept if order value >= MIN_ORDER_VALUE AND size >= min_order_size
                        # Be more strict to avoid exchange rejections
                        if order_value >= MIN_ORDER_VALUE and size >= min_order_size:
                            filtered_buy_sizes.append(size)
                    buy_order_sizes = filtered_buy_sizes
                    
                    # For sell orders: filter based on minimum order value AND minimum size
                    filtered_sell_sizes = []
                    for size in sell_order_sizes:
                        order_value = size * best_sell_price
                        # Accept if order value >= MIN_ORDER_VALUE AND size >= min_order_size
                        if order_value >= MIN_ORDER_VALUE and size >= min_order_size:
                            filtered_sell_sizes.append(size)
                    sell_order_sizes = filtered_sell_sizes
                    
                    # Adjust num_orders to actual number of orders we can place
                    actual_buy_orders = len(buy_order_sizes)
                    actual_sell_orders = len(sell_order_sizes)
                    if actual_buy_orders < num_orders or actual_sell_orders < num_orders:
                        print(f"[INFO] Adjusted order count: {actual_buy_orders} buy orders, {actual_sell_orders} sell orders (due to minimum size/value requirements)")
                    
                    if actual_buy_orders == 0:
                        print(f"[WARNING] Cannot place any buy orders - orders don't meet minimum value (5 USDT) and size ({min_order_size}) requirements")
                    if actual_sell_orders == 0:
                        print(f"[WARNING] Cannot place any sell orders - orders don't meet minimum value (5 USDT) and size ({min_order_size}) requirements")
                    
                    total_buy_value = sum(size * best_buy_price for size in buy_order_sizes)
                    total_sell_value = sum(size * best_sell_price for size in sell_order_sizes)
                    total_exposure = total_buy_value + total_sell_value
                    
                    # SAFETY FEATURE 3: Position size cap - limit total exposure
                    max_exposure_usdt = current_total_balance_usdt * (max_exposure_pct / 100.0)
                    if total_exposure > max_exposure_usdt:
                        exposure_scale = max_exposure_usdt / total_exposure
                        print(f"[SAFETY] ⚠ Total exposure {total_exposure:.2f} USDT exceeds {max_exposure_pct}% limit ({max_exposure_usdt:.2f} USDT)")
                        print(f"[SAFETY] Scaling down orders by {exposure_scale:.3f} to meet exposure limit")
                        
                        # Scale down both buy and sell orders proportionally
                        buy_order_sizes = [s * exposure_scale for s in buy_order_sizes]
                        sell_order_sizes = [s * exposure_scale for s in sell_order_sizes]
                        
                        # Recalculate values after scaling
                        total_buy_value = sum(size * best_buy_price for size in buy_order_sizes)
                        total_sell_value = sum(size * best_sell_price for size in sell_order_sizes)
                        total_exposure = total_buy_value + total_sell_value
                        
                        # Update actual order counts
                        buy_order_sizes = [s for s in buy_order_sizes if s > 0 and s >= min_order_size]
                        sell_order_sizes = [s for s in sell_order_sizes if s > 0 and s >= min_order_size]
                        actual_buy_orders = len(buy_order_sizes)
                        actual_sell_orders = len(sell_order_sizes)
                    
                    print(f"[CALC] Available: {available_usdt:.2f} USDT, {available_tokens:.2f} {token_symbol.upper()}")
                    print(f"[CALC] Total Buy Orders: {sum(buy_order_sizes):.2f} {token_symbol.upper()} (~{total_buy_value:.2f} USDT)")
                    print(f"[CALC] Total Sell Orders: {sum(sell_order_sizes):.2f} {token_symbol.upper()} (~{total_sell_value:.2f} USDT)")
                    print(f"[CALC] Total Exposure: {total_exposure:.2f} USDT ({total_exposure/current_total_balance_usdt*100:.1f}% of balance)")
                    
                    # Final validation: ensure we're not trying to spend more than available
                    if total_buy_value > available_usdt * 0.95:
                        print(f"[ERROR] Total buy value {total_buy_value:.2f} USDT exceeds available {available_usdt:.2f} USDT!")
                        print(f"[ERROR] This should not happen - recalculating order sizes...")
                        # Recalculate with stricter limit
                        max_buy_tokens = (available_usdt * 0.90) / best_buy_price
                        buy_total_order_size = min(buy_total_order_size, max_buy_tokens)
                        buy_order_sizes = calculate_order_sizes(buy_total_order_size, num_orders, effective_min_buy)
                        buy_order_sizes = [s for s in buy_order_sizes if s > 0]
                        actual_buy_orders = len(buy_order_sizes)
                        total_buy_value = sum(size * best_buy_price for size in buy_order_sizes)
                        print(f"[CALC] Recalculated: {actual_buy_orders} buy orders, {total_buy_value:.2f} USDT total")
                    
                    # COMPLIANCE MODE: Adjust order distribution to meet LBank requirement
                    # Requirement: 500-1000 USDT TOTAL (buy + sell) within ±1% of market price
                    if compliance_mode:
                        # Calculate how many orders fit within ±1% (0.25% steps: 0%, 0.25%, 0.5%, 0.75%, 1.0%)
                        # Orders 0-4 are within ±1% (5 orders total)
                        orders_within_1pct = 5
                        
                        # Target: concentrate compliance_min_usdt to compliance_max_usdt TOTAL within ±1%
                        target_compliance_value = compliance_max_usdt  # Target the maximum (1000 USDT)
                        
                        # Limit to only orders within ±1%
                        buy_order_sizes_1pct = buy_order_sizes[:min(orders_within_1pct, len(buy_order_sizes))]
                        sell_order_sizes_1pct = sell_order_sizes[:min(orders_within_1pct, len(sell_order_sizes))]
                        
                        # Calculate current value within ±1%
                        buy_value_within_1pct = sum(size * best_buy_price for size in buy_order_sizes_1pct)
                        sell_value_within_1pct = sum(size * best_sell_price for size in sell_order_sizes_1pct)
                        total_value_within_1pct = buy_value_within_1pct + sell_value_within_1pct
                        
                        print(f"[COMPLIANCE] Target: {target_compliance_value:.2f} USDT TOTAL within ±1%")
                        print(f"[COMPLIANCE] Current within ±1%: {total_value_within_1pct:.2f} USDT (Buy: {buy_value_within_1pct:.2f}, Sell: {sell_value_within_1pct:.2f})")
                        
                        # If total exceeds max, scale down proportionally
                        if total_value_within_1pct > compliance_max_usdt:
                            scale_factor = compliance_max_usdt / total_value_within_1pct
                            print(f"[COMPLIANCE] Scaling down by {scale_factor:.3f} to meet {compliance_max_usdt} USDT max")
                            
                            # Scale both buy and sell proportionally
                            buy_order_sizes_1pct = [s * scale_factor for s in buy_order_sizes_1pct]
                            sell_order_sizes_1pct = [s * scale_factor for s in sell_order_sizes_1pct]
                            
                            buy_value_within_1pct = sum(size * best_buy_price for size in buy_order_sizes_1pct)
                            sell_value_within_1pct = sum(size * best_sell_price for size in sell_order_sizes_1pct)
                            total_value_within_1pct = buy_value_within_1pct + sell_value_within_1pct
                        
                        # If total is below minimum, try to increase (if balance allows)
                        elif total_value_within_1pct < compliance_min_usdt:
                            additional_needed = compliance_min_usdt - total_value_within_1pct
                            total_available = available_usdt + (available_tokens * best_sell_price)
                            
                            if total_available >= compliance_min_usdt:
                                # Split additional needed proportionally (50/50 buy/sell)
                                buy_additional = additional_needed * 0.5
                                sell_additional = additional_needed * 0.5
                                
                                # Ensure we don't exceed available balance
                                buy_additional = min(buy_additional, available_usdt * 0.90 - buy_value_within_1pct)
                                sell_additional = min(sell_additional, (available_tokens * best_sell_price * 0.90) - sell_value_within_1pct)
                                
                                # Distribute additional tokens across orders 0-4
                                if buy_additional > 0 and len(buy_order_sizes_1pct) > 0:
                                    additional_buy_tokens = buy_additional / best_buy_price
                                    per_order = additional_buy_tokens / len(buy_order_sizes_1pct)
                                    buy_order_sizes_1pct = [s + per_order for s in buy_order_sizes_1pct]
                                
                                if sell_additional > 0 and len(sell_order_sizes_1pct) > 0:
                                    additional_sell_tokens = sell_additional / best_sell_price
                                    per_order = additional_sell_tokens / len(sell_order_sizes_1pct)
                                    sell_order_sizes_1pct = [s + per_order for s in sell_order_sizes_1pct]
                                
                                if buy_additional > 0 or sell_additional > 0:
                                    print(f"[COMPLIANCE] Increased orders within ±1% (+{buy_additional:.2f} buy, +{sell_additional:.2f} sell)")
                            
                            # Recalculate after adjustment
                            buy_value_within_1pct = sum(size * best_buy_price for size in buy_order_sizes_1pct)
                            sell_value_within_1pct = sum(size * best_sell_price for size in sell_order_sizes_1pct)
                            total_value_within_1pct = buy_value_within_1pct + sell_value_within_1pct
                        
                        # Replace order sizes with compliance-adjusted sizes
                        buy_order_sizes = buy_order_sizes_1pct
                        sell_order_sizes = sell_order_sizes_1pct
                        
                        # Filter out orders that don't meet minimums
                        buy_order_sizes = [s for s in buy_order_sizes if s > 0 and s >= min_order_size]
                        sell_order_sizes = [s for s in sell_order_sizes if s > 0 and s >= min_order_size]
                        actual_buy_orders = len(buy_order_sizes)
                        actual_sell_orders = len(sell_order_sizes)
                        
                        # Final compliance check
                        final_buy_value_1pct = sum(size * best_buy_price for size in buy_order_sizes)
                        final_sell_value_1pct = sum(size * best_sell_price for size in sell_order_sizes)
                        final_total_1pct = final_buy_value_1pct + final_sell_value_1pct
                        
                        print(f"[COMPLIANCE] Final value within ±1%: {final_total_1pct:.2f} USDT (Buy: {final_buy_value_1pct:.2f}, Sell: {final_sell_value_1pct:.2f})")
                        
                        if compliance_min_usdt <= final_total_1pct <= compliance_max_usdt:
                            print(f"[COMPLIANCE] ✓ Requirement met: {final_total_1pct:.2f} USDT is within {compliance_min_usdt}-{compliance_max_usdt} USDT range")
                        elif final_total_1pct < compliance_min_usdt:
                            print(f"[COMPLIANCE] ⚠ Warning: {final_total_1pct:.2f} USDT < {compliance_min_usdt} USDT (insufficient balance)")
                        else:
                            print(f"[COMPLIANCE] ⚠ Warning: {final_total_1pct:.2f} USDT > {compliance_max_usdt} USDT (scaled but still high)")

                    # Clear order ID lists for new orders
                    buy_order_ids.clear()
                    sell_order_ids.clear()

                    # A loop for placing multiple orders
                    # Calculate cumulative price steps for proper distribution
                    cumulative_buy_step = 0
                    cumulative_sell_step = 0
                    
                    buy_placed = 0
                    sell_placed = 0
                    buy_failed = 0
                    sell_failed = 0
                    
                    # Use the actual number of orders we can place
                    max_orders = max(actual_buy_orders, actual_sell_orders)
                    
                    for i in range(max_orders):
                        price_step_percentage = get_price_step_percentage(
                            i, base_price_step_percentage
                        )

                        # BUY Orders
                        if not usdt_pause and i < actual_buy_orders:
                            if token_pause:
                                temp_buy_price = get_buy_price_in_spread()
                            else:
                                temp_buy_price = best_buy_price  # Use the already-capped best_buy_price from above
                            
                            # CRITICAL: Ensure buy price NEVER exceeds bid price
                            if temp_buy_price > bid_price:
                                print(f"[WARNING] Buy price ({temp_buy_price:.6f}) exceeds bid ({bid_price:.6f}), capping")
                                temp_buy_price = bid_price * 0.999

                            if i == 0:
                                buy_price = temp_buy_price
                                cumulative_buy_step = 0
                            else:
                                # Accumulate the step percentage
                                cumulative_buy_step += price_step_percentage
                                # Ensure minimum 0.25% distance for first order after base
                                if i == 1 and cumulative_buy_step < 0.0025:
                                    cumulative_buy_step = 0.0025
                                # In compliance mode, cap at 1% instead of 10%
                                max_distance = 0.01 if compliance_mode else 0.10
                                if cumulative_buy_step > max_distance:
                                    cumulative_buy_step = max_distance
                                buy_price = temp_buy_price * (1 - cumulative_buy_step)
                            
                            # FINAL CHECK: Ensure buy_price never exceeds bid
                            if buy_price > bid_price:
                                print(f"[ERROR] Calculated buy_price ({buy_price:.6f}) exceeds bid ({bid_price:.6f}), forcing to bid * 0.999")
                                buy_price = bid_price * 0.999

                            distance_pct = (cumulative_buy_step * 100) if i > 0 else 0
                            
                            # Skip if index out of range
                            if i >= len(buy_order_sizes):
                                buy_failed += 1
                                if i < 3:
                                    print(f"  [BUY #{i+1}] SKIPPED: Order not available (index out of range)")
                                continue
                            
                            # Check minimum order value (price * quantity >= 5 USDT) and minimum size
                            # Exchange requires higher minimums - be strict here
                            MIN_ORDER_VALUE = 5.0
                            order_value = buy_order_sizes[i] * buy_price
                            if order_value < MIN_ORDER_VALUE or buy_order_sizes[i] < min_order_size:
                                buy_failed += 1
                                if i < 3:
                                    print(f"  [BUY #{i+1}] SKIPPED: Order value {order_value:.2f} USDT < {MIN_ORDER_VALUE} or size {buy_order_sizes[i]:.2f} < {min_order_size}")
                                continue
                            
                            res = place_order(
                                SYMBOL,
                                "buy_maker",
                                buy_order_sizes[i],
                                buy_price,
                            )
                            # Check for success - handle different response formats
                            is_success = (
                                res.get("msg") == "Success" or 
                                res.get("result") == "true" or 
                                res.get("result") is True or
                                (res.get("data") and res.get("data").get("order_id"))
                            )
                            if is_success:
                                order_id = res.get("data", {}).get("order_id", "N/A")
                                buy_order_ids.append(order_id)
                                buy_placed += 1
                                if i < 3 or i == num_orders - 1:  # Show first 3 and last order
                                    print(f"  [BUY #{i+1}] Price: {buy_price:.6f} | Size: {buy_order_sizes[i]:.2f} | Distance: {distance_pct:.2f}% | Order ID: {order_id}")
                            else:
                                buy_failed += 1
                                error_msg = res.get("error", res.get("msg", "Unknown error"))
                                error_lower = str(error_msg).lower()
                                
                                # Handle insufficient balance - stop trying more buy orders
                                if "currency is not enough" in error_lower or "insufficient" in error_lower or "not enough" in error_lower:
                                    if i == 0:  # First order failed due to balance
                                        print(f"  [BUY #{i+1}] FAILED: Insufficient USDT balance. Need more USDT for buy orders.")
                                        print(f"  [INFO] Skipping remaining buy orders due to insufficient balance")
                                    break  # Stop trying more buy orders
                                # Handle minimum value/quantity errors
                                elif "minimum value" in error_lower or "minimum" in error_lower and ("quantity" in error_lower or "value" in error_lower):
                                    print(f"  [BUY #{i+1}] FAILED: {error_msg}")
                                    print(f"  [INFO] Order size {buy_order_sizes[i]:.2f} or value {buy_order_sizes[i] * buy_price:.2f} below exchange minimum")
                                    # Skip this and remaining orders (they'll all be too small)
                                    break
                                elif i < 3:  # Show first few other failures
                                    print(f"  [BUY #{i+1}] FAILED: {error_msg}")
                        else:
                            if i == 0:
                                print("[PAUSE] Buy orders paused (USDT balance protection)")

                        # SELL Orders
                        if not token_pause and i < actual_sell_orders:
                            # Ensure best_sell_price is valid (must be above ask price)
                            if best_sell_price <= 0 or best_sell_price < ask_price:
                                print(f"[WARNING] Invalid best_sell_price ({best_sell_price:.6f}), recalculating from ask_price {ask_price:.6f}")
                                best_sell_price = ask_price * 1.02
                            
                            if i == 0:
                                sell_price = best_sell_price
                                cumulative_sell_step = 0
                            else:
                                # Accumulate the step percentage
                                cumulative_sell_step += price_step_percentage
                                # Ensure minimum 0.25% distance for first order after base
                                if i == 1 and cumulative_sell_step < 0.0025:
                                    cumulative_sell_step = 0.0025
                                # SAFETY FEATURE 4: Dynamic distance adjustment for wide spreads
                                if compliance_mode:
                                    max_distance = 0.01  # 1% in compliance mode
                                elif reduce_distance_on_wide_spread and spread_pct > wide_spread_threshold:
                                    # Reduce max distance to 5% when spread > 20%
                                    max_distance = 0.05
                                else:
                                    max_distance = 0.10  # Default 10%
                                
                                if cumulative_sell_step > max_distance:
                                    cumulative_sell_step = max_distance
                                # Use best_sell_price (which is above ask) as base
                                sell_price = best_sell_price * (1 + cumulative_sell_step)
                            
                            # Final validation: ensure sell price is above ask price
                            if sell_price < ask_price:
                                print(f"[WARNING] Sell price {sell_price:.6f} below ask {ask_price:.6f}, adjusting")
                                sell_price = ask_price * 1.02
                            
                            # Skip if index out of range
                            if i >= len(sell_order_sizes):
                                sell_failed += 1
                                if i < 3:
                                    print(f"  [SELL #{i+1}] SKIPPED: Order not available (index out of range)")
                                continue
                            
                            # Check minimum order value (price * quantity >= 5 USDT) and minimum size
                            # Exchange requires higher minimums - be strict here
                            MIN_ORDER_VALUE = 5.0
                            order_value = sell_order_sizes[i] * sell_price
                            if order_value < MIN_ORDER_VALUE or sell_order_sizes[i] < min_order_size:
                                sell_failed += 1
                                if i < 3:
                                    print(f"  [SELL #{i+1}] SKIPPED: Order value {order_value:.2f} USDT < {MIN_ORDER_VALUE} or size {sell_order_sizes[i]:.2f} < {min_order_size}")
                                continue
                            
                            distance_pct = (cumulative_sell_step * 100) if i > 0 else 0
                            res = place_order(
                                SYMBOL, "sell_maker", sell_order_sizes[i], sell_price
                            )
                            # Check for success - handle different response formats
                            is_success = (
                                res.get("msg") == "Success" or 
                                res.get("result") == "true" or 
                                res.get("result") is True or
                                (res.get("data") and res.get("data").get("order_id"))
                            )
                            if is_success:
                                order_id = res.get("data", {}).get("order_id", "N/A")
                                sell_order_ids.append(order_id)
                                sell_placed += 1
                                if i < 3 or i == num_orders - 1:  # Show first 3 and last order
                                    print(f"  [SELL #{i+1}] Price: {sell_price:.6f} | Size: {sell_order_sizes[i]:.2f} | Distance: {distance_pct:.2f}% | Order ID: {order_id}")
                            else:
                                sell_failed += 1
                                error_msg = res.get("error", res.get("msg", "Unknown error"))
                                error_lower = str(error_msg).lower()
                                
                                # Handle insufficient balance - stop trying more sell orders
                                if "currency is not enough" in error_lower or "insufficient" in error_lower or "not enough" in error_lower:
                                    if i == 0:  # First order failed due to balance
                                        print(f"  [SELL #{i+1}] FAILED: Insufficient {token_symbol.upper()} balance. Need more tokens for sell orders.")
                                        print(f"  [INFO] Skipping remaining sell orders due to insufficient balance")
                                    break  # Stop trying more sell orders
                                # Handle minimum value/quantity errors
                                elif "minimum value" in error_lower or "minimum" in error_lower and ("quantity" in error_lower or "value" in error_lower):
                                    print(f"  [SELL #{i+1}] FAILED: {error_msg}")
                                    print(f"  [INFO] Order size {sell_order_sizes[i]:.2f} or value {sell_order_sizes[i] * sell_price:.2f} below exchange minimum")
                                    # Skip this and remaining orders (they'll all be too small)
                                    break
                                # Handle price validation errors
                                elif "price must not be lower" in error_lower or "price must not be higher" in error_lower:
                                    print(f"  [SELL #{i+1}] FAILED: {error_msg}")
                                    # Skip this order and continue with next
                                    continue
                                elif i < 3:  # Show first few other failures
                                    print(f"  [SELL #{i+1}] FAILED: {error_msg}")
                        else:
                            if i == 0:
                                print("[PAUSE] Sell orders paused (Token balance protection)")
                    
                    print(f"\n[SUMMARY] Buy Orders: {buy_placed} placed, {buy_failed} failed | Sell Orders: {sell_placed} placed, {sell_failed} failed")
                    print(f"[SUMMARY] Total Active Orders: {len(buy_order_ids) + len(sell_order_ids)}")
                    
                    # Check balance AFTER placing orders to detect any changes
                    balance_after_orders = fetch_account_balance()
                    usdt_free_after = balance_after_orders["usdt"]["free"]
                    usdt_locked_after = balance_after_orders["usdt"]["locked"]
                    usdt_total_after = usdt_free_after + usdt_locked_after
                    token_free_after = balance_after_orders[token_symbol]["free"]
                    token_locked_after = balance_after_orders[token_symbol]["locked"]
                    token_total_after = token_free_after + token_locked_after
                    
                    # Calculate changes
                    usdt_change_this_iter = usdt_total_after - total_usdt_before
                    token_change_this_iter = token_total_after - total_tokens_before
                    
                    # Show locked funds in orders
                    if usdt_locked_after > 0 or token_locked_after > 0:
                        print(f"[BALANCE] After orders: USDT {usdt_free_after:.2f} free + {usdt_locked_after:.2f} locked = {usdt_total_after:.2f} total")
                        print(f"[BALANCE] After orders: {token_symbol.upper()} {token_free_after:.2f} free + {token_locked_after:.2f} locked = {token_total_after:.2f} total")
                    
                    # Warn if USDT decreased significantly (likely from filled buy orders)
                    if usdt_change_this_iter < -0.1:  # More than 0.1 USDT decrease
                        print(f"[WARNING] ⚠ USDT decreased by {abs(usdt_change_this_iter):.2f} USDT this iteration!")
                        print(f"[WARNING] This likely means buy orders filled (consuming USDT) without matching sell fills")
                        print(f"[WARNING] Check if sell orders are too far from market price to fill")
                    
                    # Track if tokens increased (from filled buy orders)
                    if token_change_this_iter > 0.1:
                        print(f"[INFO] Tokens increased by {token_change_this_iter:.2f} (likely from filled buy orders)")

                    sleep_time = get_dynamic_sleep_time(current_volatility)
                    print(f"\n[WAIT] Sleeping for {sleep_time:.1f} seconds before next iteration...")
                    time.sleep(sleep_time)

            except Exception as e:
                print(f"\n[ERROR] An error occurred in iteration {iteration}: {e}")
                traceback.print_exc()
                print("[WAIT] Waiting 10 seconds before retrying...")
                time.sleep(10)
    except KeyboardInterrupt:
        print("\n\n[STOP] Bot stopped by user (Ctrl+C)")
        print("[CLEANUP] Cancelling all active orders...")
        if buy_order_ids:
            print(f"[CLEANUP] Cancelling {len(buy_order_ids)} buy orders...")
            cancel_list_of_orders(SYMBOL, buy_order_ids)
        if sell_order_ids:
            print(f"[CLEANUP] Cancelling {len(sell_order_ids)} sell orders...")
            cancel_list_of_orders(SYMBOL, sell_order_ids)
        print("[CLEANUP] All orders cancelled. Bot stopped.")
