**Translation to English:**

Since you are now using a simple bot with limited capabilities (custom code) and not Hummingbot/ready-made platform, I will give you setup and operation rules that can be directly converted to programming logic (Parameters + execution steps) aiming to:
*   Meet the platform requirement: Order book depth within ±1% = 500–1000 USDT
*   Maintain Spread close to/under 1% as much as possible
*   Reduce ST/EST wash trade risk via a "healthy" and continuous order book
*   Add capital protections (Pause / Kill-switch / Volatility guard / Inventory guard)

Important note: The platform said “depth within ±1% to 500–1000 USDT” — they most likely mean visible depth within ±1%. Practically, the best and safest approach:
✅ Make it 500 USDT per side (buy + sell) = 1000 USDT total within ±1%
If capital doesn't allow, as a minimum, make it 250 per side then increase gradually.

---

**1) Basic Settings (Constant Inputs)**
*   Tick size: 0.00001
*   Min order: 10 ACCES
*   Target depth within ±1%:
    *   `TARGET_DEPTH_PER_SIDE = 500` (USDT)  (Highest safety)
    *   Or 250 if needed temporarily
*   Number of levels within ±1% per side:
    *   `LEVELS_PER_SIDE = 10` (Excellent with tick=0.00001)
    *   (If your bot is very limited: 6 levels)
*   Order refresh:
    *   `REFRESH_SECONDS = 25` to 45 seconds (Don't make it too fast to reduce sniping and API requests)
    *   `REPRICE_ON_MOVE = true` (Re-centers the ladder if price moves)

---

**2) Calculate the ±1% Range (for price 0.02 or 0.015)**

If Price (Mid / Last) = 0.02000
*   Lower Bound: `LOW = 0.02000 * 0.99 = 0.01980`
*   Upper Bound: `HIGH = 0.02000 * 1.01 = 0.02020`

If Price = 0.01500
*   `LOW = 0.01485`
*   `HIGH = 0.01515`

Use Mid Price if available (best bid + best ask / 2), otherwise use Last.

---

**3) Distributing Levels within ±1% (Ladder)**

Price step for each level within ±1%

Make the levels "equally spaced" within ±1%:
*   `STEP_PCT = 1% / LEVELS_PER_SIDE`
*   If `LEVELS_PER_SIDE = 10` → `STEP_PCT = 0.1%`

Examples at 0.02000
*   Buy levels (Bids) within ±1%:
    *   0.01990, 0.01988, 0.01986 ... down to 0.01980
*   Sell levels (Asks):
    *   0.02010, 0.02012, 0.02014 ... up to 0.02020

With tick=0.00001 you can make a much smoother gradient, which reduces "price jumps" and makes spread easier.

---

**4) Order Size per Level to Achieve 500 USDT Depth Per Side**

We want the total order value within ±1% per side ≈ `TARGET_DEPTH_PER_SIDE`.

Therefore:
*   `DEPTH_PER_LEVEL_USDT = TARGET_DEPTH_PER_SIDE / LEVELS_PER_SIDE`
*   Then convert it to ACCES quantity:
*   `QTY_PER_LEVEL_ACCES = DEPTH_PER_LEVEL_USDT / PRICE_LEVEL`

Example 1: Price ~0.020 and target $500 per side and 10 levels
*   `DEPTH_PER_LEVEL_USDT = 500/10 = 50 USDT`
*   At price 0.02:
*   `QTY ≈ 50 / 0.02 = 2,500 ACCES` per level

Thus, within ±1% you place:
*   10 buy orders × ~2,500 ACCES
*   10 sell orders × ~2,500 ACCES

Total within ±1%:
*   Buys ≈ $500
*   Sells ≈ $500

Example 2: Price ~0.015 and target $500 and 10 levels
*   `DEPTH_PER_LEVEL_USDT = 50`
*   `QTY ≈ 50 / 0.015 = 3,333 ACCES` per level

If the bot is limited and cannot handle 10 levels:
Use 6 levels and make `DEPTH_PER_LEVEL_USDT = 500/6 ≈ 83.33` →
And at 0.02 the quantity ≈ 4,166 ACCES per level.

---

**5) Required Spread and How to Ensure It**

The platform cares about spread as it's a "live" liquidity indicator.

Practical target:
*   `TARGET_TOTAL_SPREAD = 0.8% to 1.0%` (if possible)

How?
*   Make the closest buy order and closest sell order near the price:

Simple setup:
*   `BEST_BID = MID * (1 - 0.40%)`
*   `BEST_ASK = MID * (1 + 0.40%)`
→ Total spread ≈ 0.8%

Then build the rest of the levels until you reach ±1%.

If the market is very volatile, raise it to 0.5%/0.5% (1% spread).
If liquidity is weak and you need quick improvement, start at 0.4% then adjust gradually.

---

**6) Capital Protections (Essential Now)**

This is the most important point because a "limited bot" can bleed quickly without safeguards.

**(A) Volatility Kill-Switch**

Pause the bot if abnormal movement occurs:
*   If price moves:
    *   `>= 2%` within 60 seconds → `PAUSE 10` minutes
    *   Or `>= 5%` within 5 minutes → `PAUSE 30` minutes
*   During Pause:
    *   Cancel all open orders
    *   Wait until volatility returns to normal

**(B) Spread Guard**

If the spread suddenly widens (sign of sniping/liquidity vacuum):
*   If `spread > 1.5%` for 2 minutes:
    *   Cancel orders
    *   Rebuild the ladder with a temporarily wider spread (e.g., 1.2% total)
    *   Then gradually return

**(C) Inventory Guard (Prevent one-sided bleeding)**

Set limits for your portfolio balance:
*   Target balance: 50/50 by value (USDT vs ACCES)
*   If ACCES value becomes `> 65%` of total (due to downturn and filled buys):
    *   Reduce buy orders (lower `TARGET_DEPTH_PER_SIDE` for buys by 30–50%)
    *   Or widen bids away
*   If USDT value becomes `> 65%` (due to upturn and filled sells):
    *   Reduce sell orders using the same logic

**(D) Max Fill / Anti-Sniping**

To reduce "sniping":
*   Don't update orders every 2 seconds (this makes them snipe you)
*   Use:
    *   `REFRESH_SECONDS = 25–45`
    *   And slight randomness ±3 seconds
*   If more than:
    *   3 orders are filled within 30 seconds → Stop for 5 minutes (likely an attacking market maker)

---

**7) Step-by-Step Operation Logic (For Programming)**
1.  Read Price
    *   MID or LAST
2.  Calculate ±1% bounds
    *   LOW / HIGH
3.  Determine closest level
    *   `BEST_BID = MID*(1-0.4%)`
    *   `BEST_ASK = MID*(1+0.4%)`
4.  Build level prices within ±1%
    *   10 bids levels from `BEST_BID` down to `LOW`
    *   10 asks levels from `BEST_ASK` up to `HIGH`
    *   Each price rounded to tick size 0.00001
5.  Calculate quantity per level
    *   `QTY = (TARGET_DEPTH_PER_SIDE/LEVELS_PER_SIDE) / PRICE_LEVEL`
    *   Ensure it's `≥ 10 ACCES`
6.  Place Limit orders
    *   bids + asks
7.  Monitor every 5–10 seconds
    *   Spread / Depth within ±1% / Fill speed / Price movement
8.  Repositioning
    *   If MID moves more than `0.3%` from the last mid used to build the ladder:
    *   Cancel all
    *   Rebuild ladder
9.  Apply Protections
    *   Kill switch / Pause / Inventory guard

---

**8) "Quick Temporary" Ready-to-Use Settings (Choose One)**

Option A (Excellent & Meets Requirements)
*   `LEVELS_PER_SIDE = 10`
*   `TARGET_DEPTH_PER_SIDE = 500 USDT`
*   `BEST_SPREAD_SIDE = 0.40%` (0.8% total)
*   `REFRESH = 30s`
*   Kill switch: `2%/1m pause 10m`

Option B (Lighter on Capital/Bot)
*   `LEVELS_PER_SIDE = 6`
*   `TARGET_DEPTH_PER_SIDE = 400 USDT`
*   `BEST_SPREAD_SIDE = 0.50%` (1% total)
*   `REFRESH = 35s`

---

**One question that lets me finalize the "exact numbers" for you without any assumptions:**

Do you want to achieve 500–1000 USDT within ±1% as:
1.  Per side (500 buy + 500 sell)
or
2.  Total for both sides (e.g., 250 buy + 250 sell = 500 total)

If you tell me which one, I will immediately give you:
*   A ready-made price/quantity table at 0.020 and at 0.015
*   And a tidy "Parameters" version as a list ready to hand over to the programmer.
