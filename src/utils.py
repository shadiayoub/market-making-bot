import logging
import numpy as np
import os
from dotenv import load_dotenv
from lbank.old_api import BlockHttpClient
from datetime import datetime, timedelta, timezone

# Load environment variables from .env file
load_dotenv()

# Get API credentials from environment variables
API_KEY = os.getenv("LBANK_API_KEY", "")
API_SECRET = os.getenv("LBANK_API_SECRET", "")
SIGN_METHOD = os.getenv("LBANK_SIGN_METHOD", "HMACSHA256")  # HMACSHA256 or RSA
BASE_URL = os.getenv("LBANK_BASE_URL", "https://api.lbkex.com/")

# Get trading pair configuration
pair = os.getenv("TRADING_PAIR", "acces_usdt")
token_symbol = os.getenv("TOKEN_SYMBOL", "acces")

# Validate that API credentials are set
if not API_KEY or not API_SECRET:
    raise ValueError(
        "API credentials not found! Please set LBANK_API_KEY and LBANK_API_SECRET in .env file"
    )

client = BlockHttpClient(
    sign_method=SIGN_METHOD,
    api_key=API_KEY,
    api_secret=API_SECRET,
    base_url=BASE_URL,
    log_level=logging.ERROR,
)


def get_order_book(symbol):
    """
    Fetch the order book for a given symbol.

    Parameters:
    - symbol: Trading pair symbol (e.g., pair)

    Returns:
    - dict: Order book data, or empty dict on error
    """
    try:
        api_url = "v2/supplement/ticker/bookTicker.do"
        payload = {"symbol": symbol}
        return client.http_request("get", api_url, payload=payload)
    except Exception as e:
        print(f"[ERROR] Failed to fetch order book for {symbol}: {e}")
        return {}


def get_buy_price_in_spread():
    """
    Get buy price within spread (2% below ask price).
    
    Returns:
    - float: Buy price, or 0.0 on error
    """
    try:
        order_book = get_order_book(pair)
        
        if not order_book:
            raise Exception("Empty order book response")
        
        # Check if result indicates success
        result = order_book.get("result")
        if result != "true" and result is not True:
            error_msg = order_book.get("error", order_book.get("msg", "Unknown error"))
            raise Exception(f"API error: {error_msg}")
        
        data = order_book.get("data", {})
        if not data:
            raise Exception("No data in order book response")
        
        ask_price = float(data.get("askPrice", 0))
        if ask_price == 0:
            raise Exception("Invalid ask price")
        
        # Calculate the maximum allowable ask price based on a 2% spread
        max_ask_price = ask_price * 0.98
        return max_ask_price
    except Exception as e:
        print(f"[WARNING] Error in get_buy_price_in_spread: {e}")
        # Try to get current price as fallback
        try:
            current_price = get_current_price(pair)
            fallback_price = current_price * 0.98
            print(f"[FALLBACK] Using current price fallback: {fallback_price:.6f}")
            return fallback_price
        except:
            print("[ERROR] Could not get fallback price for buy orders")
            return 0.0


def get_sell_price_in_spread():
    """
    Get sell price within spread (should be above ask price, not bid price).
    
    Returns:
    - float: Sell price, or 0.0 on error
    """
    try:
        order_book = get_order_book(pair)
        
        if not order_book:
            raise Exception("Empty order book response")
        
        # Check if result indicates success
        result = order_book.get("result")
        if result != "true" and result is not True:
            error_msg = order_book.get("error", order_book.get("msg", "Unknown error"))
            raise Exception(f"API error: {error_msg}")
        
        data = order_book.get("data", {})
        if not data:
            raise Exception("No data in order book response")
        
        ask_price = float(data.get("askPrice", 0))
        if ask_price == 0:
            raise Exception("Invalid ask price")
        
        # For sell orders, we should be above the ask price (what sellers are asking)
        # Add 2% above ask price to ensure we're above market
        sell_price = ask_price * 1.02
        return sell_price
    except Exception as e:
        print(f"[WARNING] Error in get_sell_price_in_spread: {e}")
        # Try to get current price as fallback
        try:
            current_price = get_current_price(pair)
            fallback_price = current_price * 1.02
            print(f"[FALLBACK] Using current price fallback: {fallback_price:.6f}")
            return fallback_price
        except:
            print("[ERROR] Could not get fallback price for sell orders")
            return 0.0


def place_order(symbol, side, amount, price=None):
    """
    Place an order on the exchange.

    Parameters:
    - symbol: Trading pair symbol (e.g., pair)
    - side: Order side ("buy_maker"/"buy" or "sell_maker"/"sell") - will be converted to "buy"/"sell" per API docs
    - price: Price at which to place the order
    - amount: Amount of the asset to trade

    Returns:
    - dict: Response from the exchange
    """
    # v1 endpoints may require RSA signature, v2 endpoints work with HMACSHA256
    # Since we're using HMACSHA256, prioritize v2 endpoints
    # Note: v2/supplement/create_order.do is the main endpoint per library code
    paths_to_try = ["v2/supplement/create_order.do", "v2/create_order.do"]
    
    # For v2 endpoints, keep original order types (buy_maker/sell_maker)
    # For v1 endpoints, convert to buy/sell per API documentation
    # We'll handle this per endpoint in the loop below
    
    # Try different symbol formats
    # Order creation works with lowercase (acces_usdt) - try that first
    # Order book uses lowercase, order creation works with lowercase
    symbol_formats = [
        symbol.lower(),            # Lowercase first (this works for order creation)
        symbol,                    # Original format
        symbol.upper(),            # Uppercase (for orders query, but not creation)
        # Less likely formats - try only if above fail
        symbol.replace("_", ""),   # No underscore: accesusdt
        symbol.upper().replace("_", ""),  # ACCESUSDT
    ]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_formats = []
    for fmt in symbol_formats:
        if fmt not in seen:
            seen.add(fmt)
            unique_formats.append(fmt)
    symbol_formats = unique_formats
    
    last_error = None
    attempts = 0
    total_attempts = len(paths_to_try) * len(symbol_formats)
    
    for path in paths_to_try:
        # Determine order type based on endpoint version
        # v1 endpoints use "buy"/"sell", v2 endpoints use "buy_maker"/"sell_maker"
        if path.startswith("v1/"):
            # v1 endpoint - convert to buy/sell
            if side == "buy_maker":
                order_type = "buy"
            elif side == "sell_maker":
                order_type = "sell"
            else:
                order_type = side
        else:
            # v2 endpoint - keep original buy_maker/sell_maker
            order_type = side
        
        for idx, symbol_format in enumerate(symbol_formats):
            attempts += 1
            payload = {
                "symbol": symbol_format,
                "type": order_type,
                "amount": amount,
            }

            if price is not None:
                payload["price"] = price

            try:
                res = client.http_request("post", path, payload=payload)
                
                # Check response
                if res:
                    result = res.get("result")
                    error_msg = res.get("error", res.get("msg", ""))
                    error_lower = str(error_msg).lower() if error_msg else ""
                    
                    # If successful, return immediately
                    if result == "true" or result is True or res.get("msg") == "Success":
                        if (symbol_format != symbol or path != paths_to_try[0]) and attempts > 1:
                            print(f"[INFO] Order placed using endpoint '{path}' and symbol format: '{symbol_format}'")
                        return res
                    
                    # Store the error for reporting
                    last_error = error_msg
                    
                    # If it's a "nonsupport" error, try next combination
                    if "nonsupport" in error_lower or "not support" in error_lower or "unsupported" in error_lower:
                        if attempts == 1:  # Only print on first attempt
                            print(f"[INFO] Trying different endpoints and symbol formats for order placement...")
                        # Continue to next combination
                        if idx < len(symbol_formats) - 1:
                            continue
                        elif path == paths_to_try[0]:  # Try next path
                            break
                        else:
                            # All combinations tried
                            return res
                    else:
                        # Non-format error, return immediately
                        return res
                else:
                    # Empty response, try next combination if available
                    if idx < len(symbol_formats) - 1:
                        continue
                    elif path == paths_to_try[0]:
                        break
                    else:
                        return res
                        
            except Exception as e:
                last_error = str(e)
                # If this is the last combination, return error
                if attempts >= total_attempts:
                    return {"result": False, "error": str(e), "msg": str(e)}
                # Otherwise try next combination
                continue
    
    # If we get here, all combinations failed
    error_msg = last_error or "All endpoints and symbol formats failed"
    print(f"[ERROR] Failed to place order after {attempts} attempts. Last error: {error_msg}")
    return {"result": False, "error": error_msg, "msg": error_msg}


def cancel_all_orders(symbol):
    """
    Cancel all orders for a given symbol.

    Parameters:
    - symbol: Trading pair symbol (e.g., pair)

    Returns:
    - dict: Response from the exchange
    """

    path = "v2/supplement/cancel_order_by_symbol.do"
    payload = {"symbol": symbol}
    return client.http_request("POST", path, payload=payload)


def cancel_one_order(symbol, order_id):
    """
    Cancel One order

    Parameters:
    - symbol: Trading pair symbol (e.g., pair)
    - order_id : Order of the id that you need to cancel

    Returns:
    - dict: Response from the exchange
    """
    path = "v2/supplement/cancel_order.do"
    payload = {"symbol": symbol, "orderId": order_id}
    return client.http_request("POST", path, payload=payload)


def cancel_list_of_orders(symbol, order_ids):
    """
    Cancel a List of orders used to not intrrupt the other orders

    Parameters:
    - symbol: Trading pair symbol (e.g., pair)
    - order_ids : List of Order ids that you need to cancel

    """
    if not order_ids:
        return
    cancelled = 0
    failed = 0
    for order_id in order_ids[:]:  # Use slice to avoid modification during iteration
        try:
            res = cancel_one_order(symbol, order_id)
            if res.get("result") == "true" or res.get("msg") == "Success":
                cancelled += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
        order_ids.remove(order_id)
    if cancelled > 0 or failed > 0:
        print(f"[CANCEL] Cancelled {cancelled} orders, {failed} failed")


def get_current_price(symbol):
    """
    Get the current price for a given symbol.

    Parameters:
    - symbol: Trading pair symbol (e.g., pair)

    Returns:
    - float: Current price of the trading pair
    """
    try:
        path = "v2/supplement/ticker/price.do"
        payload = {"symbol": symbol}
        res = client.http_request("GET", path, payload=payload)
        
        if not res:
            raise Exception("Empty response from API")
        
        # Check if result indicates success
        result = res.get("result")
        if result == "true" or result is True:
            data = res.get("data", [])
            if isinstance(data, list) and len(data) > 0:
                price_data = data[0]
                if isinstance(price_data, dict):
                    current_price = price_data.get("price")
                else:
                    current_price = price_data
                return float(current_price)
            else:
                raise Exception("No price data in response")
        else:
            error_msg = res.get("error", res.get("msg", "Unknown error"))
            raise Exception(f"API error: {error_msg}")
    except Exception as e:
        print(f"[ERROR] Failed to get current price for {symbol}: {e}")
        raise


def calculate_order_size(
    order_type, volatility, max_order_size, min_order_size, risk_percentage=None
):
    """
    Calculate the order size based on risk management.

    Parameters:
    - order_type: The type of order ('buy' or 'sell').
    - volatility: The current market volatility.
    - max_order_size: The maximum allowed size for an order.
    - min_order_size: The minimum allowed size for an order.
    - risk_percentage: Optional risk percentage of the account balance to use per trade.

    Returns:
    - order_size: The calculated order size.
    """
    current_price = get_current_price(pair)

    # Fetch account balance
    account_balances = fetch_account_balance()

    if order_type == "sell":
        # Use the token_symbol balance for sell orders
        asset_balance = account_balances[token_symbol]["free"]
    elif order_type == "buy":
        # Use the USDT balance for buy orders
        usdt_balance = account_balances["usdt"]["free"]
        # Convert USDT balance to token_symbol
        asset_balance = usdt_balance / current_price

    # Optionally apply a risk percentage if provided
    # For market making, use a conservative percentage to leave room for multiple orders
    if risk_percentage is not None:
        risk_amount = asset_balance * risk_percentage
    else:
        # Use 80% of balance to leave some buffer for fees and multiple orders
        risk_amount = asset_balance * 0.80

    # Ensure max_order_size does not exceed the available balance
    if max_order_size > risk_amount:
        max_order_size = risk_amount

    # Adjust order size based on volatility
    volatility_adjustment = 1 / (volatility + 1)

    # Calculate the raw order size
    if order_type == "buy":
        # For buy orders: convert USDT to token amount
        # Leave 5% buffer for fees and rounding
        available_usdt = account_balances["usdt"]["free"] * 0.95
        raw_order_size = (available_usdt * volatility_adjustment) / current_price
    else:
        # For sell orders: use token balance directly
        # Leave 5% buffer for fees and rounding
        raw_order_size = account_balances[token_symbol]["free"] * 0.95 * volatility_adjustment

    # Ensure the order size is within defined limits and doesn't exceed available balance
    order_size = max(min(raw_order_size, max_order_size, risk_amount), min_order_size)

    return order_size


def get_dynamic_sleep_time(volatility):
    """
    Get dynamic sleep time based on market volatility.

    Parameters:
    - volatility: Current market volatility

    Returns:
    - int: Dynamic sleep time in seconds
    """

    # Initialize parameters
    base_sleep_time = 8  # Base sleep time in seconds
    max_sleep_time = 20  # Maximum sleep time in seconds
    min_sleep_time = 1  # Minimum sleep time in seconds

    # Adjust sleep time based on volatility
    if volatility > 0.05:  # High volatility threshold
        sleep_time = base_sleep_time / 2
    elif volatility < 0.02:  # Low volatility threshold
        sleep_time = base_sleep_time * 2
    else:
        sleep_time = base_sleep_time

    # Ensure sleep time is within limits
    sleep_time = max(min(sleep_time, max_sleep_time), min_sleep_time)

    return sleep_time


def calculate_percentage_change(initial_balance, current_balance):
    """
    Calculate percentage change between initial and current balance.
    
    Parameters:
    - initial_balance: Initial balance value
    - current_balance: Current balance value
    
    Returns:
    - float: Percentage change, or 0.0 if initial_balance is 0
    """
    if initial_balance == 0:
        return 0.0
    change = ((current_balance - initial_balance) / initial_balance) * 100
    return change


def fetch_historical_prices(period):
    """
    Fetch historical prices for a given period.

    Parameters:
    - period: Number of minutes of historical data to fetch

    Returns:
    - list: Historical price data (closing prices)
    """
    path = "v2/kline.do"
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(minutes=period)

    # Convert dates to timestamps in seconds
    end_timestamp = int(end_date.timestamp())
    start_timestamp = int(start_date.timestamp())

    payload = {
        "symbol": pair,
        "type": "minute1",
        "size": period,
        "time": start_timestamp,
    }
    
    try:
        response = client.http_request("get", path, payload=payload)
        
        # Check if request was successful
        if response.get("result") != "true" and response.get("result") is not True:
            raise Exception(f"Failed to fetch historical prices: {response.get('error', response.get('msg', 'Unknown error'))}")
        
        # Extract kline data - format is typically: [timestamp, open, high, low, close, volume, ...]
        data = response.get("data", [])
        
        if not data or len(data) == 0:
            raise Exception("No historical price data returned")
        
        # Extract closing prices (index 4 in kline data)
        # Handle both list of lists and list of dicts formats
        prices = []
        for item in data:
            if isinstance(item, list) and len(item) > 4:
                # Format: [timestamp, open, high, low, close, volume, ...]
                prices.append(float(item[4]))
            elif isinstance(item, dict):
                # Format: {"close": price, ...}
                prices.append(float(item.get("close", item.get("c", 0))))
            else:
                # Try to convert directly if it's a number
                try:
                    prices.append(float(item))
                except (ValueError, TypeError):
                    continue
        
        if len(prices) == 0:
            raise Exception("No valid price data found in response")
        
        return prices
        
    except Exception as e:
        # Return a default list with current price if fetch fails
        try:
            current_price = get_current_price(pair)
            # Return a list with the current price repeated to avoid empty array
            return [current_price] * max(period, 10)
        except:
            # Last resort: return a small default list
            return [1.0] * max(period, 10)


def calculate_price_changes(price_data):
    """
    Calculate price changes from historical price data.

    Parameters:
    - price_data: List of historical prices

    Returns:
    - numpy.array: Array of price changes
    """
    # Ensure we have valid data
    if not price_data or len(price_data) < 2:
        # Return a default small volatility value
        return np.array([0.001])
    
    # Calculate price changes from historical price data
    prices = np.array(price_data)
    
    # Ensure prices is at least 1D and has more than 1 element
    if prices.ndim == 0 or len(prices) < 2:
        return np.array([0.001])
    
    price_changes = np.diff(prices) / prices[:-1]
    return price_changes


def calculate_standard_deviation(price_changes):
    """
    Calculate the standard deviation of price changes.

    Parameters:
    - price_changes: Array of price changes

    Returns:
    - float: Standard deviation of price changes
    """
    return np.std(price_changes)


def get_dynamic_volatilit(period):
    """
    Determine the volatility of the pair through a period of time.
    Keeps increasing the period if the volatility is too low.

    Parameters:
    - period: Number of minutes

    Returns:
    - float: volatility
    """
    try:
        price_data = fetch_historical_prices(period)  # In minutes
        
        if not price_data or len(price_data) < 2:
            # Return default volatility if no data
            return 0.01
        
        price_changes = calculate_price_changes(price_data)
        
        if len(price_changes) == 0:
            return 0.01
        
        current_volatility = calculate_standard_deviation(price_changes)

        # Ensure we have a valid volatility value
        if current_volatility == 0 or np.isnan(current_volatility) or np.isinf(current_volatility):
            # Try with a longer period, but limit recursion
            if period < 300:  # Max 5 hours
                return get_dynamic_volatilit(period + 60)
            else:
                return 0.01  # Default volatility

        return max(current_volatility, 0.001)  # Ensure minimum volatility
        
    except Exception as e:
        # Return default volatility on error
        print(f"Error calculating volatility: {e}")
        return 0.01


def calculate_order_sizes(total_order_size, num_orders, min_order_size=0):
    """
    Calculate order sizes distributed across num_orders.
    Ensures all orders meet minimum size requirements.
    
    Parameters:
    - total_order_size: Total size to distribute
    - num_orders: Number of orders
    - min_order_size: Minimum size per order (optional)
    
    Returns:
    - list: Order sizes (may be fewer than num_orders if total is insufficient)
    """
    # Check if we can meet minimum for all orders
    if min_order_size > 0:
        total_min_required = min_order_size * num_orders
        if total_order_size < total_min_required:
            # Not enough for all orders - calculate how many we can make
            max_orders_with_min = int(total_order_size / min_order_size)
            
            if max_orders_with_min == 0:
                # Can't make even one order that meets minimum
                # But if total is reasonable, try to make a few smaller orders
                # Use a flexible minimum: at least 10% of total per order, or actual minimum, whichever is smaller
                flexible_min = min(min_order_size, total_order_size * 0.1)
                if flexible_min > 0:
                    # Try to make multiple orders with flexible minimum
                    max_flexible_orders = min(num_orders, int(total_order_size / flexible_min))
                    if max_flexible_orders > 0:
                        # Use decreasing distribution
                        order_sizes = []
                        remaining_percentage = 0.70
                        first_order_size = total_order_size * 0.30
                        order_sizes.append(first_order_size)
                        
                        remaining_size = total_order_size - first_order_size
                        for i in range(1, max_flexible_orders):
                            if i == max_flexible_orders - 1:
                                order_sizes.append(remaining_size)
                            else:
                                next_order_size = remaining_size * (remaining_percentage * 0.3)
                                order_sizes.append(next_order_size)
                                remaining_size -= next_order_size
                                remaining_percentage *= 0.7
                        
                        # Ensure all meet flexible minimum
                        for i in range(len(order_sizes)):
                            if order_sizes[i] < flexible_min:
                                order_sizes[i] = flexible_min
                        
                        return order_sizes
                
                # Last resort: return single order
                return [total_order_size]
            
            # We can make max_orders_with_min orders that meet minimum
            # Use decreasing distribution pattern
            order_sizes = []
            if max_orders_with_min == 1:
                order_sizes.append(total_order_size)
            else:
                remaining_percentage = 0.70
                first_order_size = total_order_size * 0.30
                order_sizes.append(first_order_size)
                
                remaining_size = total_order_size - first_order_size
                for i in range(1, max_orders_with_min):
                    if i == max_orders_with_min - 1:
                        # Last order gets the remainder
                        order_sizes.append(remaining_size)
                    else:
                        next_order_size = remaining_size * (remaining_percentage * 0.3)
                        order_sizes.append(next_order_size)
                        remaining_size -= next_order_size
                        remaining_percentage *= 0.7
                
                # Ensure all meet minimum
                for i in range(len(order_sizes)):
                    if order_sizes[i] < min_order_size:
                        order_sizes[i] = min_order_size
            
            return order_sizes
    
    # No minimum requirement - use original distribution
    order_sizes = []
    remaining_percentage = 0.70
    first_order_size = total_order_size * 0.30
    order_sizes.append(first_order_size)

    for i in range(1, num_orders):
        next_order_size = total_order_size * (remaining_percentage * 0.3)
        order_sizes.append(next_order_size)
        remaining_percentage *= 0.7

    return order_sizes


def get_price_step_percentage(order_num, base_price_step_percentage):
    if order_num < 9:
        return base_price_step_percentage
    elif order_num < 12:
        return base_price_step_percentage * 2.5
    else:
        return base_price_step_percentage * 4


def fetch_account_balance():
    """
    Fetch account balance for specified assets.

    Returns:
    - dict: Account balances for targeted assets, with default 0.0 values on error
    """
    try:
        # v1 endpoints may require RSA signature, v2 endpoints work with HMACSHA256
        # Since we're using HMACSHA256, prioritize v2 endpoints
        paths_to_try = ["v2/supplement/user_info_account.do", "v1/user_info.do"]
        
        res = None
        for path in paths_to_try:
            try:
                res = client.http_request("POST", path)
                if res:
                    break
            except Exception as e:
                if path == paths_to_try[-1]:  # Last path
                    raise
                continue
        
        if not res:
            raise Exception("Empty response from API")
        
        # Check if result indicates success
        result = res.get("result")
        if result == "true" or result is True:
            # v1 endpoint returns: {"result": "true", "info": {"free": {...}, "freeze": {...}}}
            # v2 endpoint returns: {"result": "true", "data": {"balances": [...]}}
            
            if "info" in res:
                # v1 format
                info = res.get("info", {})
                free = info.get("free", {})
                freeze = info.get("freeze", {})
                
                targeted_assets = {
                    "usdt": {
                        "free": float(free.get("usdt", 0)),
                        "locked": float(freeze.get("usdt", 0)),
                    },
                    token_symbol: {
                        "free": float(free.get(token_symbol, 0)),
                        "locked": float(freeze.get(token_symbol, 0)),
                    }
                }
            else:
                # v2 format
                data = res.get("data", {})
                balances = data.get("balances", [])
                
                targeted_assets = {"usdt": None, token_symbol: None}
                for balance in balances:
                    if isinstance(balance, dict) and balance.get("asset") in targeted_assets:
                        targeted_assets[balance["asset"]] = {
                            "free": float(balance.get("free", 0)),
                            "locked": float(balance.get("locked", 0)),
                        }
                    if all(value is not None for value in targeted_assets.values()):
                        break
                
                # Ensure we have values for both assets (default to 0 if missing)
                for asset in ["usdt", token_symbol]:
                    if targeted_assets[asset] is None:
                        targeted_assets[asset] = {"free": 0.0, "locked": 0.0}
            
            return targeted_assets
        else:
            error_msg = res.get("msg", res.get("error", "Unknown error"))
            raise Exception(f"API error: {error_msg}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch account balance: {e}")
        print("[WARNING] Using default balances (0.0) - bot may not function correctly")
        # Return default balances to prevent crashes
        return {
            "usdt": {"free": 0.0, "locked": 0.0},
            token_symbol: {"free": 0.0, "locked": 0.0}
        }


def get_current_orders(symbol=None):
    """
    Get the current pending orders

    Parameters:
    - symbol: Trading pair symbol (optional, defaults to pair from utils.py)

    Returns:
    - dict: Response from API with orders data, or empty dict on error
    """
    if symbol is None:
        symbol = pair
    
    try:
        # v1 endpoints may require RSA signature, v2 endpoints work with HMACSHA256
        # Since we're using HMACSHA256, use v2 endpoints only
        paths_to_try = ["v2/supplement/orders_info_no_deal.do"]
        
        for path in paths_to_try:
            payload = {"symbol": symbol, "current_page": "1", "page_length": "200"}
            res = client.http_request("POST", path, payload=payload)
            
            # Check if successful
            if res and (res.get("result") == "true" or res.get("result") is True):
                return res
            
            # Check if we got an error about unsupported pair
            if res:
                error_msg = res.get("error", res.get("msg", "")).lower()
                if "nonsupport" in error_msg or "not support" in error_msg or "unsupported" in error_msg:
                    # Try uppercase version
                    symbol_upper = symbol.upper()
                    if symbol_upper != symbol:
                        print(f"[INFO] Orders endpoint doesn't support '{symbol}', trying uppercase format: {symbol_upper}")
                        payload = {"symbol": symbol_upper, "current_page": "1", "page_length": "200"}
                        res = client.http_request("POST", path, payload=payload)
                        if res and (res.get("result") == "true" or res.get("result") is True):
                            return res
                
                # If it's not a format error, return the response
                if path == paths_to_try[-1]:  # Last path tried
                    return res
            else:
                # Empty response, try next path
                if path != paths_to_try[-1]:
                    continue
                return res
        
        return res if 'res' in locals() else {}
    except Exception as e:
        print(f"[ERROR] Failed to fetch current orders for {symbol or pair}: {e}")
        return {}


def get_num_of_orders(symbol=None):
    """
    Get the number of current pending orders.
    
    Parameters:
    - symbol: Trading pair symbol (optional, defaults to pair from utils.py)
    
    Returns:
    - int: Number of orders, or 0 if error or no orders
    """
    try:
        response = get_current_orders(symbol)
        
        # Check if response is valid
        if not response:
            return 0
        
        # Handle different response formats
        # Check if result indicates success
        result = response.get("result")
        if result == "true" or result is True:
            # Try to get orders from data
            data = response.get("data", {})
            if isinstance(data, dict):
                orders = data.get("orders", [])
            elif isinstance(data, list):
                orders = data
            else:
                orders = []
            
            return len(orders) if orders else 0
        else:
            # API returned an error - but don't print if it's just "no orders" or "unsupported pair"
            error_msg = response.get("error", response.get("msg", "Unknown error"))
            error_lower = str(error_msg).lower()
            
            # If it's an unsupported pair error, just return 0 silently
            if "nonsupport" in error_lower or "not support" in error_lower or "unsupported" in error_lower:
                # This pair might not support order queries, just assume 0 orders
                return 0
            else:
                # Other errors, print for debugging
                print(f"API error getting orders: {error_msg}")
            return 0
            
    except KeyError as e:
        print(f"KeyError in get_num_of_orders: {e}. Response: {response if 'response' in locals() else 'N/A'}")
        return 0
    except Exception as e:
        print(f"Error in get_num_of_orders: {e}")
        return 0
