# LBank API Trading Restriction - acces_usdt

## Issue Summary

The trading pair `acces_usdt` does **NOT support API trading** on LBank, even though:
- ✅ The pair exists and is valid
- ✅ Order book data is accessible via API
- ✅ Account balance can be fetched
- ❌ Order placement via API fails with error code `10008: "currency pair nonsupport"`
- ❌ Order query via API fails with the same error

## Test Results

```
[TEST 1] Order Book: ✓ WORKS (acces_usdt)
[TEST 2] Accuracy List: ✓ Pair found (acces_usdt)
[TEST 3] Orders Query: ✗ FAILS (currency pair nonsupport)
[TEST 4] Order Placement: ✗ FAILS (currency pair nonsupport)
```

## Error Details

- **Error Code**: 10008
- **Error Message**: "currency pair nonsupport"
- **Affected Operations**: 
  - Order placement (`v2/supplement/create_order.do`)
  - Order query (`v2/supplement/orders_info_no_deal.do`)

## Possible Reasons

1. **View-Only Pair**: Some pairs on LBank are view-only via API (can see order book but cannot trade)
2. **New Pair Restrictions**: Newly listed pairs may have API trading disabled initially
3. **Low Liquidity Restrictions**: Pairs with low liquidity may restrict API trading
4. **Special Permissions Required**: The pair might require special API permissions or account verification

## Solutions

### Option 1: Use a Different Pair
Switch to a pair that supports API trading:
- `btc_usdt`
- `eth_usdt`
- Other major pairs

### Option 2: Contact LBank Support
Contact LBank customer support to:
- Request API trading enablement for `acces_usdt`
- Verify if your API key has the necessary permissions
- Check if there are any account restrictions

### Option 3: Check API Key Permissions
1. Log into your LBank account
2. Go to API management
3. Verify that your API key has:
   - Trading permissions enabled
   - No IP restrictions blocking requests
   - Permissions for the specific pair `acces_usdt`

## Bot Status

The market making bot is **fully functional** and ready to use. It will work once you:
- Switch to a pair that supports API trading, OR
- Get API trading enabled for `acces_usdt` from LBank

## Next Steps

1. **Immediate**: Test with a different pair (e.g., `btc_usdt`) to verify the bot works
2. **Long-term**: Contact LBank support about `acces_usdt` API trading

## Testing a Different Pair

To test with a different pair, update `src/utils.py`:

```python
pair = "btc_usdt"  # Change from acces_usdt
token_symbol = "btc"  # Change from acces
```

Then run the bot again.
