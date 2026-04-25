# Final Recommendation

## Executive conclusion
Evidence supports a faster invalidation framework for left-tail control, but only with explicit safeguards on winner preservation and data-quality gating.

## Data coverage and trust summary
- Dates analyzed: 16
- Confidence buckets: {'HIGH': 7, 'UNUSABLE': 4, 'LOW': 4, 'MEDIUM': 1}

## Strategy reconstruction summary
- Signal generation is candle-color based continuation/reversal with entry buffer triggers.
- Exit precedence prioritizes manual/hard-stop/early-risk/path-risk before target/time-stop.
- Runtime is event-driven websocket with tick-based path metrics.

## Baseline performance summary
- Trade count: 557
- Win rate: 0.71
- Net PnL: -123275.00
- Profit factor: 0.82
- Max loss: -22275.00

## Tail concentration summary
- Worst-1 loss concentration: -22275.00
- Worst-3 loss concentration: -52675.00
- Worst-5 loss concentration: -78100.00

## Top rule table
### Conservative rule
- Rule id: `R_STALE_AND_NEG_0p5s`
- Definition: stale_quote_0p5s == 1 and pnl_0p5s <= 0
- Checkpoint: 0.50s
- Winner preservation: 1.00
- Tail capture: 0.00
- Post-rule net PnL: -43925.00
### Balanced rule
- Rule id: `R_PNL_LE_0_3s`
- Definition: pnl_3s <= 0
- Checkpoint: 3.00s
- Winner preservation: 0.75
- Tail capture: 0.80
- Post-rule net PnL: 183350.00
### Aggressive rule
- Rule id: `R_PNL_LE_0_5s`
- Definition: pnl_5s <= 0
- Checkpoint: 5.00s
- Winner preservation: 0.73
- Tail capture: 0.83
- Post-rule net PnL: 180725.00

## Policy shortlist
### Best conservative policy
- Policy id: `H_MICROSTRUCTURE_GATED`
- Rule: Exit 1s if stale_quote_1s==1 OR spread_vs_entry_1s>2, with non-positive pnl
- Net PnL: -31925.00
- Winners lost: 0
- Tail losers prevented: 0
### Best balanced policy
- Policy id: `C_FAST_INVALIDATION_HARDSTOP`
- Rule: Exit at 2s if runup_2s < 0.75; else exit at 5s if drawdown_5s <= -4
- Net PnL: 162252.15
- Winners lost: 61
- Tail losers prevented: 25
### Best aggressive policy
- Policy id: `C_FAST_INVALIDATION_HARDSTOP`
- Rule: Exit at 2s if runup_2s < 0.75; else exit at 5s if drawdown_5s <= -4
- Net PnL: 162252.15
- Winners lost: 61
- Tail losers prevented: 25

## Winner vs loser early-shape takeaway
- adverse_before_favorable_rate: winners=0.24, losers=0.81, delta=-0.57
- positive_pnl_rate_0p5s: winners=0.34, losers=0.10, delta=0.24
- positive_pnl_rate_1s: winners=0.59, losers=0.16, delta=0.43
- positive_pnl_rate_2s: winners=0.70, losers=0.14, delta=0.55
- positive_pnl_rate_3s: winners=0.73, losers=0.12, delta=0.62
- positive_pnl_rate_5s: winners=0.72, losers=0.14, delta=0.58

## Operational forensics summary
- Operational-failure share: 0.51
- Frequent issue: stale quote observed; missing early updates
- Frequent issue: loss looks strategy-policy driven

## Implementation blueprint
1. Start with conservative checkpoint rule in shadow mode.
2. Gate only left-tail candidates while monitoring winner preservation daily.
3. Promote to active only if day-wise holdouts remain stable.

## Limitations
- Small sample size on some dates may overstate rule robustness.
- Some dates lack full-depth option tape; fallback relies on trade-scoped capture.

## Next logging improvements needed
- Ensure consistent full lifecycle event IDs for every trade.
- Preserve per-checkpoint quote freshness counters in enriched output.
- Store explicit counterfactual fill confidence per simulated checkpoint.