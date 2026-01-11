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


def market_making(
    max_order_size,
    min_order_size,
    num_orders=20,
    base_price_step_percentage=0.0025,
):
    global SYMBOL  # Declare global at function level
    
    print("=" * 60)
    print("Market Making Bot Starting...")
    print(f"Trading Pair: {SYMBOL}")
    print(f"Token Symbol: {token_symbol}")
    print(f"Number of Positions: {num_orders} (per side)")
    print(f"Order Distance Range: 0.25% - 10% from market price")
    print(f"Max Order Size: {max_order_size} tokens")
    print(f"Min Order Size: {min_order_size} tokens")
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
        print(f"[INIT] Initial USDT Balance: {initial_usdt_balance:.2f} USDT")
        print(f"[INIT] Initial {token_symbol.upper()} Balance: {initial_token_balance:.2f} {token_symbol.upper()}")
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
                usdt_balance = balance["usdt"]["free"] + balance["usdt"]["locked"]
                token_balance = balance[token_symbol]["free"] + balance[token_symbol]["locked"]

                usdt_change = calculate_percentage_change(
                    initial_usdt_balance, usdt_balance
                )
                token_change = calculate_percentage_change(
                    initial_token_balance, token_balance
                )
                
                print(f"[BALANCE] USDT: {usdt_balance:.2f} USDT (Change: {usdt_change:+.2f}%)")
                print(f"[BALANCE] {token_symbol.upper()}: {token_balance:.2f} {token_symbol.upper()} (Change: {token_change:+.2f}%)")

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

                    # Check if there are existing orders and cancel them
                    print("[ORDERS] Checking existing orders...")
                    current_orders_number = get_num_of_orders(SYMBOL)
                    print(f"[ORDERS] Found {current_orders_number} existing orders")
                    
                    # Always cancel all orders to start fresh each iteration
                    # This prevents order accumulation and ensures clean state
                    if current_orders_number > 0:
                        print("[CANCEL] Cancelling all existing orders to start fresh...")
                        cancel_all_orders(SYMBOL)
                        sell_order_ids.clear()
                        buy_order_ids.clear()
                        print("[CANCEL] All orders cancelled")

                    # best_prices = get_best_price()
                    # best_sell_price = best_prices["best_sell"]
                    # best_buy_price = best_prices["best_buy"]
                    # best_sell_price = base_sell_price

                    # Get the best prices for selling and buying for a low market
                    best_buy_price = get_buy_price_in_spread()
                    best_sell_price = get_sell_price_in_spread()
                    
                    # Validate sell price is above ask price (critical for sell orders)
                    if best_sell_price <= 0 or best_sell_price < ask_price:
                        print(f"[WARNING] best_sell_price ({best_sell_price:.6f}) is invalid or below ask ({ask_price:.6f}), recalculating")
                        best_sell_price = ask_price * 1.02
                    
                    print(f"[PRICE] Best Buy Price: {best_buy_price:.6f} | Best Sell Price: {best_sell_price:.6f} (Ask: {ask_price:.6f})")

                    print("[CALC] Calculating order sizes...")
                    
                    # Get current balances for validation
                    current_balance = fetch_account_balance()
                    available_usdt = current_balance["usdt"]["free"]
                    available_tokens = current_balance[token_symbol]["free"]
                    
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
                    
                    # For buy orders, if total is below minimum, we may have a single order below minimum
                    # Check minimum order value instead (price * quantity >= 1 USDT typically)
                    if len(buy_order_sizes) > 0 and buy_order_sizes[0] < min_order_size:
                        # Check if order value meets minimum (1 USDT)
                        order_value = buy_order_sizes[0] * best_buy_price
                        if order_value >= 1.0:
                            print(f"[INFO] Buy order size {buy_order_sizes[0]:.2f} is below token minimum {min_order_size}, but order value {order_value:.2f} USDT meets minimum")
                        else:
                            print(f"[WARNING] Buy order value {order_value:.2f} USDT is below 1.0 USDT minimum. Skipping buy orders.")
                            buy_order_sizes = []
                    
                    # Ensure sell orders meet minimum
                    sell_order_sizes = [s for s in sell_order_sizes if s >= min_order_size]
                    
                    # Adjust num_orders to actual number of orders we can place
                    actual_buy_orders = len(buy_order_sizes)
                    actual_sell_orders = len(sell_order_sizes)
                    if actual_buy_orders < num_orders or actual_sell_orders < num_orders:
                        print(f"[INFO] Adjusted order count: {actual_buy_orders} buy orders, {actual_sell_orders} sell orders (due to minimum size requirements)")
                    
                    if actual_buy_orders == 0:
                        print(f"[WARNING] Cannot place any buy orders - total size {buy_total_order_size:.2f} is below minimum {min_order_size} per order")
                    if actual_sell_orders == 0:
                        print(f"[WARNING] Cannot place any sell orders - total size {sell_total_order_size:.2f} is below minimum {min_order_size} per order")
                    
                    total_buy_value = sum(size * best_buy_price for size in buy_order_sizes)
                    total_sell_value = sum(size * best_sell_price for size in sell_order_sizes)
                    print(f"[CALC] Available: {available_usdt:.2f} USDT, {available_tokens:.2f} {token_symbol.upper()}")
                    print(f"[CALC] Total Buy Orders: {sum(buy_order_sizes):.2f} {token_symbol.upper()} (~{total_buy_value:.2f} USDT)")
                    print(f"[CALC] Total Sell Orders: {sum(sell_order_sizes):.2f} {token_symbol.upper()} (~{total_sell_value:.2f} USDT)")
                    
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
                                best_buy_price = get_buy_price_in_spread()
                            else:
                                best_buy_price = base_buy_price

                            if i == 0:
                                buy_price = best_buy_price
                                cumulative_buy_step = 0
                            else:
                                # Accumulate the step percentage
                                cumulative_buy_step += price_step_percentage
                                # Ensure minimum 0.25% distance for first order after base
                                if i == 1 and cumulative_buy_step < 0.0025:
                                    cumulative_buy_step = 0.0025
                                # Cap at 10% maximum distance
                                if cumulative_buy_step > 0.10:
                                    cumulative_buy_step = 0.10
                                buy_price = best_buy_price * (1 - cumulative_buy_step)

                            distance_pct = (cumulative_buy_step * 100) if i > 0 else 0
                            
                            # Skip if order size is too small
                            if i >= len(buy_order_sizes) or buy_order_sizes[i] < min_order_size:
                                buy_failed += 1
                                if i < 3:
                                    print(f"  [BUY #{i+1}] SKIPPED: Order size too small or not available")
                                continue
                            
                            # Check minimum order value (price * quantity)
                            order_value = buy_order_sizes[i] * buy_price
                            if order_value < 1.0:  # Minimum order value is typically 1 USDT
                                buy_failed += 1
                                if i < 3:
                                    print(f"  [BUY #{i+1}] SKIPPED: Order value {order_value:.2f} USDT below minimum 1.0 USDT")
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
                                # Cap at 10% maximum distance
                                if cumulative_sell_step > 0.10:
                                    cumulative_sell_step = 0.10
                                # Use best_sell_price (which is above ask) as base
                                sell_price = best_sell_price * (1 + cumulative_sell_step)
                            
                            # Final validation: ensure sell price is above ask price
                            if sell_price < ask_price:
                                print(f"[WARNING] Sell price {sell_price:.6f} below ask {ask_price:.6f}, adjusting")
                                sell_price = ask_price * 1.02
                            
                            # Skip if order size is too small
                            if i >= len(sell_order_sizes) or sell_order_sizes[i] < min_order_size:
                                sell_failed += 1
                                if i < 3:
                                    print(f"  [SELL #{i+1}] SKIPPED: Order size too small or not available")
                                continue
                            
                            # Check minimum order value (price * quantity)
                            order_value = sell_order_sizes[i] * sell_price
                            if order_value < 1.0:  # Minimum order value is typically 1 USDT
                                sell_failed += 1
                                if i < 3:
                                    print(f"  [SELL #{i+1}] SKIPPED: Order value {order_value:.2f} USDT below minimum 1.0 USDT")
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
