from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_pipeline.cli import build_arg_parser, run_pipeline_from_args


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    summary = run_pipeline_from_args(args)

    print("usable dates:", ", ".join(summary.usable_dates) if summary.usable_dates else "none")
    print("excluded dates:", ", ".join(summary.excluded_dates) if summary.excluded_dates else "none")
    print("total trades seen:", summary.total_trades_seen)
    print("reconciled closed trades:", summary.reconciled_closed_trades)
    print("best simple 1-second rule:", summary.best_simple_1s_rule or "none")
    print("best simple 3-second rule:", summary.best_simple_3s_rule or "none")
    print("best scenario policy:", summary.best_scenario_policy or "none")
    print("estimated tail-loss reduction:", summary.estimated_tail_loss_reduction)
    print("key caveat:", summary.key_caveat or "")


if __name__ == "__main__":
    main()
