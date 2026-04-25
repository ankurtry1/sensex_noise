from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelineConfig:
    repo_root: Path
    output_dir: Path
    start_date: str | None = None
    end_date: str | None = None
    include_archived: bool = False
    skip_plots: bool = False
    min_trades_per_day: int = 1
    verbose: bool = False

    @property
    def logs_dir(self) -> Path:
        return self.repo_root / "logs"

    @property
    def analysis_dir(self) -> Path:
        return self.output_dir if self.output_dir.is_absolute() else self.repo_root / self.output_dir

    @property
    def figures_dir(self) -> Path:
        return self.analysis_dir / "figures"


@dataclass
class PipelineRunSummary:
    usable_dates: list[str]
    excluded_dates: list[str]
    total_trades_seen: int
    reconciled_closed_trades: int
    best_simple_1s_rule: str | None
    best_simple_3s_rule: str | None
    best_scenario_policy: str | None
    estimated_tail_loss_reduction: float | None
    key_caveat: str
