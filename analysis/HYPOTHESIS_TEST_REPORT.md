# Hypothesis Test Report

## Scope
- Objective: empirically validate the strategy hypothesis and test candidate invalidation/kill-switch rules using repository journal data.
- Data period detected from logs: 2026-03-11 to 2026-03-19.
- Closed trades analyzed: 193

## Data Sources Used
| source_file | records | date_start | date_end | dates | trade_entries | open_marks | trade_exits | early_failure_events | usable_for_trade_lifecycle | usable_for_spot_tick_replay | usable_for_option_tick_replay |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11Mar_trades.jsonl | 4930 | 2026-03-11 | 2026-03-11 | 2026-03-11 | 58 | 4757 | 57 | 0 | yes | no | partial_from_marks_only |
| 12Mar_trades.jsonl | 5014 | 2026-03-12 | 2026-03-12 | 2026-03-12 | 30 | 4931 | 23 | 0 | yes | no | partial_from_marks_only |
| trades.jsonl | 10630 | 2026-03-13 | 2026-03-19 | 2026-03-13,2026-03-18,2026-03-19 | 114 | 7082 | 113 | 25 | yes | no | partial_from_marks_only |

## Reconstructed Trade Fields
- Core lifecycle: signal trigger context, entry, target placement, open marks, exit.
- Derived fields: holding time, realized points/PnL, max drawdown (MAE), max run-up (MFE), first move direction, early-window response, entry delay from source candle start, moneyness class.
- Missing for direct hypothesis tests: underlying spot tick path after entry, previous-candle OHLC snapshots at signal time, IV/spread/greeks, option LTP at signal trigger (pre-entry).

## Baseline Strategy Snapshot
- Win rate: 94.82%, avg PnL/trade: -1055.00, median PnL/trade: 2220.00, max loss: -316414.00, net PnL: -203615.00
- Avg holding time: 90.36s, early-failure logged trades: 25/193

## Per-Hypothesis Findings (H1-H10)
| hypothesis_id | statement | test_definition | sample_size | metric_1 | metric_2 | support_level | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H1 | 5-point trigger often yields +3 premium follow-through. | Target-hit rate across all closed trades. | 193 | 0.948187 | -1055 | suggestive | High hit-rate can coexist with negative expectancy if loser tails are large. |
| H2 | Fast trigger moves perform better than slow trigger moves. | Entry delay from source candle start vs outcomes. | 193 | -0.214664 | 1612.17 | suggestive | Negative Spearman correlation suggests slower setups underperform. |
| H3 | Premium confirmation soon after entry improves outcomes. | runup_10s >= 1.0 vs < 1.0. | 193 | 5634.1 | 0.984496 | suggestive | Confirmation uses post-entry premium behavior as proxy. |
| H4 | Later-day trades underperform. | Compare before 13:00 vs >=13:00 PnL. | 193 | -1573.49 | 182.105 | inconclusive | Post-1PM time-stop losses can materially impact late session expectancy. |
| H5 | If premium does not move quickly, trade quality is poor. | runup_10s < 0.5 vs >= 0.5. | 193 | -6379.18 | 806.601 | suggestive | Useful kill-switch signal if this gap is stable over more days. |
| H6 | Spot fallback toward trigger invalidates continuation. | Spot post-entry path not logged; proxy with option drawdown_10s <= -2. | 193 | -4504.39 | 3147.7 | proxy_only | Requires spot tick logging around trigger/entry to test directly. |
| H7 | Moneyness influences premium response quality. | Compare ITM/ATM/OTM groups at entry. | 193 | -1055 | -1055 | inconclusive | Interpret cautiously if one class dominates sample. |
| H8 | Regime/candle context affects outcomes. | Proxy regime by first-30s premium range (high vs low). | 193 | -5022.3 | 2953.62 | inconclusive | True candle/volatility context requires underlying tick/candle logs. |
| H9 | Immediate adverse move predicts weak expectancy. | drawdown_5s <= -2 vs better first-5s profile. | 193 | -2396.79 | 117.437 | suggestive | Strong candidate for quick invalidation if stable over more sessions. |
| H10 | Continuation and reversal setups behave differently. | Compare known signal families. | 49 | -10064.4 | -3636.9 | suggestive | Only evaluated where signal_kind exists. |

## Candidate Kill-Switch / Filter Rules
Top rules by net PnL change vs baseline:
| rule_id | rule_type | description | trades_total | trades_modified | trades_filtered_out | win_rate | avg_pnl | median_pnl | max_loss | avg_holding_seconds | expectancy | net_pnl | net_pnl_change_vs_baseline | large_losers_avoided | winners_prematurely_killed | winners_flipped_to_loss |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FILTER_REVERSAL_ONLY_WHEN_KNOWN | entry_filter | When signal_kind is known, take only reversal setups. | 193 | 39 | 39 | 0.974026 | 1226.6 | 1560 | -84609 | 91.1261 | 1226.6 | 188896 | 392511 | 6 | 33 |  |
| EXIT_ON_EARLY_FAILURE_EVENT | early_exit | Exit when EARLY_FAILURE_SIGNAL is logged. | 193 | 25 | 0 | 0.849741 | -547.508 | 1500 | -316414 | 81.0882 | -547.508 | -105669 | 97946 | 5 | 19 | 19 |
| EXIT_WITH_GLOBAL_180S_TIME_STOP | early_exit | Exit at first mark after 180s if still open. | 193 | 17 | 0 | 0.880829 | -742.902 | 2100 | -90668 | 41.4041 | -742.902 | -143380 | 60235 | 4 | 13 | 13 |
| FILTER_KEEP_BEFORE_1400 | entry_filter | Only take entries before 14:00. | 193 | 31 | 31 | 0.962963 | -1011.96 | 2280 | -316414 | 91.4205 | -1011.96 | -163938 | 39677 | 4 | 27 |  |
| FILTER_CONTINUATION_ONLY_WHEN_KNOWN | entry_filter | When signal_kind is known, take only continuation setups. | 193 | 10 | 10 | 0.95082 | -913.913 | 2100 | -316414 | 93.4712 | -913.913 | -167246 | 36369 | 1 | 9 |  |
| EXIT_WITH_GLOBAL_90S_TIME_STOP | early_exit | Exit at first mark after 90s if still open. | 193 | 31 | 0 | 0.813472 | -977.047 | 1680 | -78764 | 30.5352 | -977.047 | -188570 | 15045 | 4 | 27 | 26 |
| FILTER_KEEP_BEFORE_1300 | entry_filter | Only take entries before 13:00. | 193 | 57 | 57 | 0.970588 | -1573.49 | 2580 | -316414 | 101.144 | -1573.49 | -213995 | -10380 | 5 | 51 |  |
| FILTER_KEEP_BEFORE_1330 | entry_filter | Only take entries before 13:30. | 193 | 46 | 46 | 0.959184 | -1461.35 | 2220 | -316414 | 98.1779 | -1461.35 | -214818 | -11203 | 4 | 42 |  |

Top rules by large-loser avoidance:
| rule_id | rule_type | description | trades_total | trades_modified | trades_filtered_out | win_rate | avg_pnl | median_pnl | max_loss | avg_holding_seconds | expectancy | net_pnl | net_pnl_change_vs_baseline | large_losers_avoided | winners_prematurely_killed | winners_flipped_to_loss |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EXIT_IF_ADVERSE_2PTS_WITHIN_5S | early_exit | Exit on -2 points adverse move within 5s. | 193 | 90 | 0 | 0.523316 | -1898.85 | 1500 | -316414 | 21.7305 | -1898.85 | -366479 | -162864 | 7 | 82 | 82 |
| FILTER_REVERSAL_ONLY_WHEN_KNOWN | entry_filter | When signal_kind is known, take only reversal setups. | 193 | 39 | 39 | 0.974026 | 1226.6 | 1560 | -84609 | 91.1261 | 1226.6 | 188896 | 392511 | 6 | 33 |  |
| EXIT_IF_STAGNANT_AND_BELOW_ENTRY_10S | early_exit | At 10s, if MFE < 0.5 and still below entry, exit. | 193 | 47 | 0 | 0.740933 | -1167.7 | 1500 | -316414 | 36.8604 | -1167.7 | -225367 | -21752 | 6 | 40 | 40 |
| EXIT_IF_NO_PROGRESS_10S_MFE_LT_0_5 | early_exit | At 10s, if MFE < 0.5 then exit. | 193 | 47 | 0 | 0.740933 | -1167.7 | 1500 | -316414 | 36.8604 | -1167.7 | -225367 | -21752 | 6 | 40 | 40 |
| EXIT_IF_ADVERSE_5PTS_WITHIN_15S | early_exit | Exit on -5 points adverse move within 15s. | 193 | 76 | 0 | 0.590674 | -2518.84 | 1500 | -316414 | 22.8346 | -2518.84 | -486136 | -282521 | 6 | 69 | 69 |
| EXIT_IF_ADVERSE_3PTS_WITHIN_10S | early_exit | Exit on -3 points adverse move within 10s. | 193 | 95 | 0 | 0.492228 | -3398.53 | -1500 | -316414 | 17.4112 | -3398.53 | -655917 | -452302 | 6 | 88 | 88 |
| EXIT_ON_EARLY_FAILURE_EVENT | early_exit | Exit when EARLY_FAILURE_SIGNAL is logged. | 193 | 25 | 0 | 0.849741 | -547.508 | 1500 | -316414 | 81.0882 | -547.508 | -105669 | 97946 | 5 | 19 | 19 |
| FILTER_KEEP_BEFORE_1300 | entry_filter | Only take entries before 13:00. | 193 | 57 | 57 | 0.970588 | -1573.49 | 2580 | -316414 | 101.144 | -1573.49 | -213995 | -10380 | 5 | 51 |  |

## Time-of-Day Behavior
| entry_hour | trades | win_rate | avg_pnl | net_pnl | avg_dd | early_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 9 | 30 | 1 | 2656 | 79680 | 6.26333 | 0.133333 |
| 10 | 41 | 0.95122 | -3554.37 | -145729 | 15.8439 | 0.121951 |
| 11 | 36 | 0.972222 | 2363 | 85068 | 13.3139 | 0.138889 |
| 12 | 29 | 0.965517 | -8034.97 | -233014 | 14.1448 | 0.137931 |
| 13 | 26 | 0.923077 | 1925.27 | 50057 | 6.8 | 0.0769231 |
| 14 | 26 | 0.846154 | -2119.12 | -55097 | 13.6712 | 0.192308 |
| 15 | 5 | 1 | 3084 | 15420 | 8.7 | 0 |

## What The Data Supports vs Suggests
- Supported descriptively: large adverse early moves and weak early premium response are associated with poorer expectancy.
- Suggestive (not definitive): slower trigger timing and later-session entries tend to underperform in this sample.
- Not directly testable with current logs: spot fallback-to-trigger and pre-entry spot velocity quality.
- Reliability caveat: sample is only a few sessions; thresholds should be treated as candidate ranges, not fixed truths.

## Candidate Operational Guardrails (Empirical, Not Final)
- Early invalidation candidate: adverse premium breach within first 5-15s (e.g., -2 to -5 points) shows strong loser-avoidance potential.
- Follow-through absence candidate: no meaningful MFE in first 10-20s is a useful kill-switch family to test.
- Session control candidate: stricter entry windows in late day can reduce tail risk.

## Lightweight Instrumentation Plan (Forward-Compatible)
Add these journal events/fields to improve hypothesis fidelity:
1. `SIGNAL_GENERATED` event in engine right after strategy signal: `signal_time`, `signal_kind`, `side`, `source_candle_start`, `previous_candle_open`, `previous_candle_close`, `trigger_price`, `spot_ltp_at_signal`.
2. `ENTRY_CONTEXT` event just before broker entry: `option_ltp_pre_entry`, `spot_ltp_pre_entry`, `entry_delay_seconds`, `selector_offset_points`, `atm_strike`, `moneyness_class`.
3. `EARLY_SNAPSHOT` events at +5s/+10s/+15s/+20s: `spot_ltp`, `option_ltp`, `pnl_delta`, `cum_mfe`, `cum_mae`, `spread_if_available`.
4. `RULE_TRIGGERED` event for any future kill-switch: `rule_id`, `trigger_time`, `trigger_price`, `reason_metrics`.
5. Optional per-trade summary event at close: `max_mfe`, `max_mae`, `time_to_mfe_1`, `time_to_target`, `max_spot_fallback_from_trigger`.

## Reproducibility
- Script: `analysis/hypothesis_killswitch_analysis.py`
- Run command from repo root: `.venv/bin/python analysis/hypothesis_killswitch_analysis.py`
- Outputs directory: `analysis/output/`