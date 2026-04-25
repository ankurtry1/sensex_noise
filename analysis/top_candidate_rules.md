# Top Candidate Rules

## Conservative
- Rule: `R_STALE_AND_NEG_0p5s`
- Definition: stale_quote_0p5s == 1 and pnl_0p5s <= 0
- Winner preservation: 1.00
- Tail capture: 0.00
- Post-rule net PnL: -43925.00

## Balanced
- Rule: `R_PNL_LE_0_3s`
- Definition: pnl_3s <= 0
- Winner preservation: 0.75
- Tail capture: 0.80
- Post-rule net PnL: 183350.00

## Aggressive
- Rule: `R_PNL_LE_0_5s`
- Definition: pnl_5s <= 0
- Winner preservation: 0.73
- Tail capture: 0.83
- Post-rule net PnL: 180725.00
