from __future__ import annotations

import pandas as pd

from analysis_pipeline.scenario_lab import simulate_policies, build_policy_specs


def test_policy_scenario_lab_schema_and_nonempty() -> None:
    df = pd.DataFrame(
        [
            {
                "trade_id": "t1",
                "net_pnl": 4.0,
                "signal_kind": "CONTINUATION_CALL",
                "pre_or_post_1pm": "PRE_1PM",
                "runup_1s": 0.2,
                "runup_2s": 0.3,
                "runup_3s": 0.5,
                "drawdown_1s": -0.8,
                "drawdown_5s": -1.5,
                "pnl_1s": 0.1,
                "pnl_2s": 0.0,
                "stale_quote_1s": 0,
                "spread_vs_entry_1s": 0.5,
                "missing_update_1s": 0,
                "quote_quality_degradation_flag": 0,
                "counterfactual_exit_pnl_1s": 0.2,
                "counterfactual_exit_pnl_2s": 0.4,
                "counterfactual_exit_pnl_3s": 0.8,
                "counterfactual_exit_pnl_5s": 1.0,
            },
            {
                "trade_id": "t2",
                "net_pnl": -8.0,
                "signal_kind": "REVERSAL_PUT",
                "pre_or_post_1pm": "POST_1PM",
                "runup_1s": 0.1,
                "runup_2s": 0.2,
                "runup_3s": 0.3,
                "drawdown_1s": -2.5,
                "drawdown_5s": -5.0,
                "pnl_1s": -1.8,
                "pnl_2s": -2.8,
                "stale_quote_1s": 1,
                "spread_vs_entry_1s": 2.5,
                "missing_update_1s": 0,
                "quote_quality_degradation_flag": 1,
                "counterfactual_exit_pnl_1s": -1.5,
                "counterfactual_exit_pnl_2s": -2.0,
                "counterfactual_exit_pnl_3s": -3.0,
                "counterfactual_exit_pnl_5s": -4.0,
            },
        ]
    )

    out = simulate_policies(df, build_policy_specs())
    assert not out.empty

    required = {
        "policy_id",
        "policy_name",
        "exact_rule_text",
        "assumptions",
        "trade_count",
        "net_pnl",
        "avg_pnl",
        "median_pnl",
        "max_loss",
        "max_gain",
        "profit_factor",
        "expectancy",
        "winners_lost",
        "losers_prevented",
        "tail_losers_prevented",
        "killed_before_1s",
        "killed_before_2s",
        "killed_before_3s",
        "killed_before_5s",
        "evaluable_trade_count",
    }
    assert required.issubset(set(out.columns))
