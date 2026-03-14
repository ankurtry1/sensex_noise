# Sensex Noise Paper Trading Repo

A Python repo for **paper trading** your Sensex options strategy using live market data from Kite Connect and a simulated wallet.

This repo does **not place real exchange orders**. It does three things:

1. watches **BSE:SENSEX** live LTP,
2. evaluates your 5-minute candle breakout rule,
3. simulates a **market buy** plus an **immediate target limit sell at entry + 3**.

It supports:
- one trade at a time,
- no concurrent positions,
- no re-entry in the same candle after exit,
- strike rounding to valid **100-point Sensex strikes**,
- nearest weekly expiry selection,
- paper wallet and P&L logging,
- pluggable charges model.

## Strategy locked into this repo

### Candle setup
- timeframe: **5 minutes**
- previous candle green: `close > open`
- previous candle red: `close < open`
- neutral candle: ignored

### Entry
- if previous candle is green and live **Sensex spot LTP** crosses `previous_close + 5`, buy **CALL**
- if previous candle is red and live **Sensex spot LTP** crosses `previous_close - 5`, buy **PUT**

### Option selection
- nearest weekly expiry
- call strike: `round_to_100(spot - 200)`
- put strike: `round_to_100(spot + 200)`

### Execution
- simulate **market buy** at current option LTP
- immediately place simulated **limit sell** at `entry_price + 3`
- exit when option LTP reaches or exceeds the target

### Position rules
- quantity: **500**
- starting wallet: **₹10,00,000**
- one open trade max
- after target exit, no re-entry in the same 5-minute candle
- no EOD forced square-off logic included
- charges model is pluggable and currently defaults to zero unless you wire yours in

## Repo structure

```
sensex-noise-papertrade/
├─ .env.example
├─ README.md
├─ requirements.txt
├─ run.py
├─ scripts/
│  ├─ check_kite_auth.py
│  └─ generate_access_token.py
├─ data/
│  └─ instruments.csv            # optional cached instrument dump
├─ logs/
├─ src/
│  └─ sensex_noise/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ models.py
│     ├─ wallet.py
│     ├─ charges.py
│     ├─ candle_state.py
│     ├─ selector.py
│     ├─ strategy.py
│     ├─ broker/
│     │  ├─ __init__.py
│     │  ├─ base.py
│     │  └─ kite_paper.py
│     └─ services/
│        ├─ __init__.py
│        ├─ instruments.py
│        ├─ market_data.py
│        └─ engine.py
└─ tests/
   └─ test_selector.py
```

## Setup

### 1) Create environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows
python3 -m pip install -r requirements.txt
```

### 2) Copy env file

```bash
cp .env.example .env
```

Fill in your Kite credentials.

## About Kite access tokens

Kite Connect’s official Python client uses `api_key`, then login flow with a `request_token`, and then generates an `access_token` for the session. The official docs also provide quote/LTP endpoints and instrument dump access for live data and symbol discovery. citeturn800223search0turn800223search3

This repo expects that you already know how to generate the access token for the current session and place it in `.env`.

## Authentication Troubleshooting

- `KITE_API_KEY`: identifies your Kite app.
- `KITE_API_SECRET`: app secret used to exchange `request_token` for session/access token.
- `KITE_REQUEST_TOKEN`: short-lived token from Kite redirect URL after login.
- `KITE_ACCESS_TOKEN`: session token used for authenticated API calls like `profile()` and `ltp()`.

Important:
- `KITE_ACCESS_TOKEN` must be generated for the same app as `KITE_API_KEY`.
- Access tokens can expire or become invalid and then market-data calls fail.
- Instrument download succeeding does not guarantee `ltp()` auth is valid for current credentials.

Run these checks/tools:

```bash
python3 scripts/check_kite_auth.py
python3 scripts/generate_access_token.py
```

If auth fails, regenerate `KITE_ACCESS_TOKEN` and update `.env`.

## Environment variables

```env
KITE_API_KEY=
KITE_API_SECRET=
KITE_ACCESS_TOKEN=
KITE_REQUEST_TOKEN=

POLL_INTERVAL_SECONDS=2
STARTING_CAPITAL=1000000
TRADE_QTY=500
ORDER_PRODUCT=MIS
TARGET_POINTS=3
ENTRY_BUFFER_POINTS=5
CALL_OFFSET_POINTS=-200
PUT_OFFSET_POINTS=200
UNDERLYING_SYMBOL=BSE:SENSEX
INSTRUMENTS_CACHE_PATH=data/instruments.csv
TRADE_LOG_PATH=logs/trades.jsonl
LOG_LEVEL=INFO
```

`ORDER_PRODUCT` supports `MIS` or `NRML` and is used for entry and exit orders.

`KITE_REQUEST_TOKEN` is not used by the engine directly, but is left here because humans keep forgetting where they put it during login ceremonies.

## Run

```bash
python3 run.py
```

## What happens when it runs

- downloads or reads the instrument dump,
- identifies valid Sensex option symbols,
- polls BSE:SENSEX LTP,
- builds current 5-minute candle state,
- on a valid trigger, selects nearest weekly option contract,
- simulates a market buy,
- immediately places a simulated target sell,
- logs trade lifecycle to console,
- appends JSON events to `TRADE_LOG_PATH` (`logs/trades.jsonl` by default).

## Important practical notes

1. This is **paper trading only**.
2. Quote and LTP availability depend on your market data access and instrument availability on Kite. Official docs note that quote APIs return data only for keys that actually exist in the response, so code must guard against missing instruments. citeturn800223search0
3. Since your target is tiny, real-world spread and slippage matter a lot.
4. Charges are currently zero by default unless you implement your own broker charge logic in `charges.py`.
5. No stop-loss logic is coded because you explicitly chose manual monitoring.

## Where to modify charges

Edit:

```python
src/sensex_noise/charges.py
```

Implement your exact broker model there.

## Safety

This repo is intentionally locked to a paper broker implementation. If you later want a live execution version, build that separately. Mixing paper logic and live logic in one button is how people manufacture regret.
