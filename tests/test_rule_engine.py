from __future__ import annotations

import pandas as pd

from analysis_pipeline.rule_engine import evaluate_rules


def test_rule_engine_outputs_expected_schema() -> None:
    df = pd.DataFrame(
        [
            {"trade_id": "t1", "net_pnl": 5, "exit_reason": "TARGET_HIT", "pnl_1s": 1, "runup_1s": 1.2, "drawdown_1s": -0.2, "pnl_3s": 2, "runup_3s": 2, "drawdown_3s": -0.5, "adverse_before_favorable": 0, "stale_quote_1s": 0},
            {"trade_id": "t2", "net_pnl": -6, "exit_reason": "EARLY_RISK_EXIT", "pnl_1s": -1.5, "runup_1s": 0.2, "drawdown_1s": -2.5, "pnl_3s": -3, "runup_3s": 0.5, "drawdown_3s": -4.0, "adverse_before_favorable": 1, "stale_quote_1s": 1},
            {"trade_id": "t3", "net_pnl": -12, "exit_reason": "HARD_STOP_EXIT", "pnl_1s": -2, "runup_1s": 0.1, "drawdown_1s": -3.2, "pnl_3s": -5, "runup_3s": 0.3, "drawdown_3s": -6.0, "adverse_before_favorable": 1, "stale_quote_1s": 0},
        ]
    )

    rule_df, labeled, specs = evaluate_rules(df)

    assert not labeled.empty
    assert not rule_df.empty
    assert len(specs) > 0
    required_cols = {
        "rule_id",
        "checkpoint",
        "rule_definition",
        "sample_size",
        "trades_killed",
        "losers_captured",
        "tail_losers_captured",
        "winners_killed",
        "winner_preservation_rate",
        "tail_capture_rate",
        "post_rule_net_pnl",
        "post_rule_expectancy",
        "post_rule_profit_factor",
        "post_rule_max_loss",
    }
    assert required_cols.issubset(set(rule_df.columns))
