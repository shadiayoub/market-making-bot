#!/usr/bin/env python3
"""
Test script to check if a trading pair supports API trading on LBank
"""
import sys
sys.path.insert(0, 'src')

from src.utils import client, pair

def test_pair_trading():
    """Test if the pair supports various API operations"""
    print(f"Testing pair: {pair}")
    print("=" * 60)
    
    # Test 1: Get order book (should work)
    print("\n[TEST 1] Getting order book...")
    try:
        from src.utils import get_order_book
        order_book = get_order_book(pair)
        if order_book.get("result") == "true" or order_book.get("result") is True:
            data = order_book.get("data", {})
            print(f"✓ Order book works")
            print(f"  Symbol in response: {data.get('symbol', 'N/A')}")
            print(f"  Bid: {data.get('bidPrice', 'N/A')}")
            print(f"  Ask: {data.get('askPrice', 'N/A')}")
        else:
            print(f"✗ Order book failed: {order_book.get('msg', 'Unknown error')}")
    except Exception as e:
        print(f"✗ Order book error: {e}")
    
    # Test 2: Get accuracy info (shows supported pairs)
    print("\n[TEST 2] Getting pair accuracy info...")
    try:
        res = client.http_request("GET", "v1/accuracy.do")
        if isinstance(res, list):
            # Find our pair in the list
            found = False
            for p in res:
                if p.get("symbol", "").lower() == pair.lower():
                    found = True
                    print(f"✓ Pair found in accuracy list")
                    print(f"  Symbol: {p.get('symbol')}")
                    print(f"  Price accuracy: {p.get('priceAccuracy')}")
                    print(f"  Quantity accuracy: {p.get('quantityAccuracy')}")
                    break
            if not found:
                print(f"✗ Pair NOT found in accuracy list")
                print(f"  Available pairs (first 10): {[p.get('symbol') for p in res[:10]]}")
            
            # Check a few popular pairs to see if they work
            print(f"\n  Testing a few popular pairs for comparison:")
            test_pairs = ["btc_usdt", "eth_usdt", "usdt_usdt"]
            for test_pair in test_pairs:
                if any(p.get("symbol", "").lower() == test_pair.lower() for p in res):
                    print(f"    {test_pair}: Found in list")
                else:
                    print(f"    {test_pair}: Not in list")
        else:
            print(f"✗ Accuracy endpoint failed: {res}")
    except Exception as e:
        print(f"✗ Accuracy error: {e}")
    
    # Test 3: Try to query orders (should work with uppercase)
    print("\n[TEST 3] Querying orders...")
    try:
        from src.utils import get_current_orders
        # Try both formats
        for test_symbol in [pair, pair.upper()]:
            print(f"  Trying symbol: {test_symbol}")
            orders = get_current_orders(test_symbol)
            if orders.get("result") == "true" or orders.get("result") is True:
                print(f"  ✓ Orders query works with '{test_symbol}'")
                break
            else:
                error = orders.get("msg", orders.get("error", "Unknown"))
                print(f"  ✗ Failed: {error}")
    except Exception as e:
        print(f"✗ Orders query error: {e}")
    
    # Test 4: Try to place a test order (will fail but shows exact error)
    print("\n[TEST 4] Attempting test order placement...")
    try:
        from src.utils import place_order
        # Try with very small amount
        test_symbols = [pair, pair.upper(), pair.lower()]
        for test_symbol in test_symbols:
            print(f"  Trying symbol: {test_symbol}")
            res = place_order(test_symbol, "buy_maker", 1.0, 0.01)
            if res.get("result") == "true" or res.get("msg") == "Success":
                print(f"  ✓ Order placement works with '{test_symbol}'!")
                break
            else:
                error = res.get("msg", res.get("error", "Unknown"))
                error_code = res.get("error_code", "N/A")
                print(f"  ✗ Failed: {error} (code: {error_code})")
                if "nonsupport" not in str(error).lower():
                    # If it's not a "nonsupport" error, we might have other issues
                    print(f"    (This might be a different issue, not just symbol format)")
    except Exception as e:
        print(f"✗ Order placement error: {e}")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("If order book works but order placement doesn't, the pair might:")
    print("1. Not support API trading (view-only)")
    print("2. Require special API permissions")
    print("3. Need a different symbol format (check accuracy list above)")

if __name__ == "__main__":
    test_pair_trading()
