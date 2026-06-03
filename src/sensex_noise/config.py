from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    kite_api_key: str
    kite_api_secret: str
    kite_access_token: str
    kite_request_token: str
    data_dir: Path
    logs_dir: Path
    runtime_dir: Path
    token_store_path: Path
    poll_interval_seconds: int
    starting_capital: float
    trade_qty: int
    order_product: str
    trading_mode: str
    position_sizing_mode: str
    capital_budget: float
    use_kite_funds: bool
    target_points: float
    entry_buffer_points: float
    call_offset_points: int
    put_offset_points: int
    underlying_symbol: str
    instruments_cache_path: Path
    trade_log_path: Path
    event_log_path: Path
    enriched_trade_log_path: Path
    features_output_path: Path
    control_path: Path
    entry_cutoff_time: str
    entry_window_seconds: int
    entry_window_max_seconds: float
    entry_feature_lookback_seconds: float
    post_1pm_time_stop_seconds: int
    session_square_off_enabled: bool
    session_square_off_time: str
    early_failure_window_seconds: int
    early_failure_mfe_min: float
    early_failure_mae_max: float
    enable_verbose_trade_logging: bool
    enable_signal_logging: bool
    enable_entry_context_logging: bool
    enable_snapshot_logging: bool
    enable_post_exit_observation: bool
    post_exit_observation_seconds: int
    post_exit_observation_interval_seconds: int
    snapshot_seconds: tuple[int, ...]
    enable_hard_stop: bool
    hard_stop_arm_after_seconds: int
    hard_stop_points: float
    continuation_call_hard_stop_points: float
    enable_microburst_gate: bool
    microburst_min_score: int
    microburst_ind_accel_threshold_1: float
    microburst_ind_accel_threshold_2: float
    microburst_opt_velocity_threshold: float
    microburst_opt_depth_imb_threshold: float
    microburst_ind_velocity_min: float
    microburst_ind_velocity_max: float
    normal_target_points: float
    promoted_min_score: int
    promoted_target_points: float
    promoted_3s_min_runup_points: float
    promoted_3s_min_pnl_points: float
    promoted_3s_max_mae_points: float
    promoted_3s_min_velocity_decay_ratio: float
    layer4_enabled: bool
    layer4_trigger_points: float
    layer4_required_followthrough_points: float
    layer4_window_seconds: float
    enable_early_risk: bool
    early_risk_suspicion_seconds: int
    early_risk_exit_seconds: int
    early_risk_runup_max_for_exit: float
    early_risk_drawdown_min_for_exit: float
    early_risk_require_below_entry: bool
    early_risk_suspicion_current_pnl: float
    early_risk_suspicion_require_adverse_first_move: bool
    early_risk_strict_after_1pm: bool
    enable_path_risk: bool
    path_risk_check_seconds: int
    path_risk_pnl_min_for_exit: float
    path_risk_runup_max_for_exit: float
    path_risk_strict_after_1pm: bool
    path_risk_tighten_if_fragile: bool
    enable_edge_invalidation: bool
    edge_invalidation_1s_enabled: bool
    edge_invalidation_3s_enabled: bool
    edge_invalidation_1s_check_seconds: float
    edge_invalidation_3s_check_seconds: float
    edge_invalidation_1s_min_runup_points: float
    edge_invalidation_1s_max_pnl_points: float
    edge_invalidation_3s_min_runup_points: float
    edge_invalidation_3s_max_drawdown_points: float
    edge_invalidation_3s_pinned_pnl_abs_points: float
    edge_invalidation_hard_stop_points: float
    edge_invalidation_hard_stop_enabled: bool
    edge_invalidation_stale_quote_max_seconds: float
    edge_invalidation_kill_on_stale_quotes: bool
    edge_invalidation_require_subsecond_precision: bool
    edge_invalidation_use_underlying_confirmation: bool
    edge_invalidation_use_spread_filter: bool
    prefer_edge_invalidation_over_legacy_early_risk: bool
    enable_dynamic_risky_target: bool
    risky_target_points: float
    strict_after_1pm_risky_target_points: float
    enable_order_timeline_logging: bool
    enable_quote_logging: bool
    enable_velocity_logging: bool
    enable_post_exit_counterfactual: bool
    enable_exit_decision_logging: bool
    enable_target_reprice_modify: bool
    enable_target_reprice_fallback_cancel_replace: bool
    enable_slippage_logging: bool
    target_reprice_debounce_seconds: int
    enable_full_option_tape_logging: bool
    enable_sensex_option_tape_recorder: bool
    sensex_tape_strike_range_points: int
    sensex_tape_strike_step_points: int
    sensex_tape_expiry_mode: str
    sensex_tape_include_ce: bool
    sensex_tape_include_pe: bool
    sensex_tape_rebase_on_atm_move_points: int
    sensex_tape_log_dir: Path
    sensex_tape_write_legacy_options_log: bool
    stream_watchdog_max_idle_seconds: int
    watchdog_hard_reconnect_seconds: int
    stream_reconnect_cooldown_seconds: int
    stream_connect_timeout_seconds: int
    stream_first_tick_timeout_seconds: int
    heartbeat_log_interval_seconds: int
    rebase_persist_ticks: int
    rebase_cooldown_seconds: int
    rebase_min_move_points: int
    critical_tick_queue_maxsize: int
    background_tick_queue_maxsize: int
    journal_queue_maxsize: int
    journal_flush_interval_seconds: int
    write_daily_features: bool
    write_daily_policy_simulation: bool
    log_level: str


def _required(name: str) -> str:
    raw = os.getenv(name)
    if raw is None:
        raise ValueError(f"Missing required environment variable: {name}. Add it to .env.")

    value = raw.strip()
    if not value:
        raise ValueError(f"Environment variable {name} is empty/whitespace. Set a valid value in .env.")
    return value


def _bool(name: str, default: str = "false") -> bool:
    raw = os.getenv(name, default).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def _resolve_path(raw: str | Path, base_dir: Path) -> Path:
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return base_dir / path


def _path_env(name: str, default: str | Path, base_dir: Path) -> Path:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        raw = str(default)
    return _resolve_path(raw, base_dir)


def _int_list(name: str, default: str) -> tuple[int, ...]:
    raw = os.getenv(name, default)
    tokens = [token.strip() for token in raw.split(",") if token.strip()]
    if not tokens:
        raise ValueError(f"{name} cannot be empty. Provide comma-separated positive integers.")

    values: list[int] = []
    for token in tokens:
        try:
            value = int(token)
        except ValueError as exc:
            raise ValueError(f"{name} contains non-integer value: {token!r}") from exc
        if value <= 0:
            raise ValueError(f"{name} values must be > 0. Found: {value}")
        values.append(value)
    return tuple(sorted(set(values)))


def _validate(settings: Settings) -> None:
    if settings.trading_mode not in {"paper", "live"}:
        raise ValueError("TRADING_MODE must be one of: paper, live")
    if settings.order_product not in {"MIS", "NRML"}:
        raise ValueError("ORDER_PRODUCT must be one of: MIS, NRML")
    if settings.position_sizing_mode not in {"fixed", "capital_based"}:
        raise ValueError("POSITION_SIZING_MODE must be one of: fixed, capital_based")

    if settings.poll_interval_seconds <= 0:
        raise ValueError("POLL_INTERVAL_SECONDS must be > 0")
    if settings.target_points <= 0:
        raise ValueError("TARGET_POINTS must be > 0")
    if settings.entry_window_seconds <= 0:
        raise ValueError("ENTRY_WINDOW_SECONDS must be > 0")
    if settings.entry_window_max_seconds <= 0:
        raise ValueError("ENTRY_WINDOW_MAX_SECONDS must be > 0")
    if settings.entry_feature_lookback_seconds <= 0:
        raise ValueError("ENTRY_FEATURE_LOOKBACK_SECONDS must be > 0")
    if settings.entry_feature_lookback_seconds > settings.entry_window_max_seconds:
        raise ValueError("ENTRY_FEATURE_LOOKBACK_SECONDS must be <= ENTRY_WINDOW_MAX_SECONDS")
    if settings.post_1pm_time_stop_seconds <= 0:
        raise ValueError("POST_1PM_TIME_STOP_SECONDS must be > 0")
    if settings.session_square_off_enabled:
        try:
            _ = settings.session_square_off_time
            from datetime import time as _dt_time

            _dt_time.fromisoformat(settings.session_square_off_time)
        except Exception as exc:
            raise ValueError(
                "SESSION_SQUARE_OFF_TIME must be HH:MM or HH:MM:SS when SESSION_SQUARE_OFF_ENABLED=true"
            ) from exc

    if settings.enable_hard_stop:
        if settings.hard_stop_points <= 0:
            raise ValueError("HARD_STOP_POINTS must be > 0 when ENABLE_HARD_STOP=true")
        if settings.continuation_call_hard_stop_points <= 0:
            raise ValueError(
                "CONTINUATION_CALL_HARD_STOP_POINTS must be > 0 when ENABLE_HARD_STOP=true"
            )
    if settings.hard_stop_arm_after_seconds < 0:
        raise ValueError("HARD_STOP_ARM_AFTER_SECONDS must be >= 0")
    if settings.microburst_min_score < 0:
        raise ValueError("MICROBURST_MIN_SCORE must be >= 0")
    if settings.promoted_min_score < settings.microburst_min_score:
        raise ValueError("PROMOTED_MIN_SCORE must be >= MICROBURST_MIN_SCORE")
    if settings.microburst_ind_accel_threshold_1 <= 0:
        raise ValueError("MICROBURST_IND_ACCEL_THRESHOLD_1 must be > 0")
    if settings.microburst_ind_accel_threshold_2 <= settings.microburst_ind_accel_threshold_1:
        raise ValueError("MICROBURST_IND_ACCEL_THRESHOLD_2 must be > MICROBURST_IND_ACCEL_THRESHOLD_1")
    if settings.microburst_opt_velocity_threshold <= 0:
        raise ValueError("MICROBURST_OPT_VELOCITY_THRESHOLD must be > 0")
    if settings.microburst_opt_depth_imb_threshold <= 0:
        raise ValueError("MICROBURST_OPT_DEPTH_IMB_THRESHOLD must be > 0")
    if settings.microburst_ind_velocity_min <= 0:
        raise ValueError("MICROBURST_IND_VELOCITY_MIN must be > 0")
    if settings.microburst_ind_velocity_max <= settings.microburst_ind_velocity_min:
        raise ValueError("MICROBURST_IND_VELOCITY_MAX must be > MICROBURST_IND_VELOCITY_MIN")
    if settings.normal_target_points <= 0:
        raise ValueError("NORMAL_TARGET_POINTS must be > 0")
    if settings.promoted_target_points <= settings.normal_target_points:
        raise ValueError("PROMOTED_TARGET_POINTS must be > NORMAL_TARGET_POINTS")
    if settings.promoted_3s_min_runup_points <= 0:
        raise ValueError("PROMOTED_3S_MIN_RUNUP_POINTS must be > 0")
    if settings.promoted_3s_min_pnl_points <= 0:
        raise ValueError("PROMOTED_3S_MIN_PNL_POINTS must be > 0")
    if settings.promoted_3s_max_mae_points <= 0:
        raise ValueError("PROMOTED_3S_MAX_MAE_POINTS must be > 0")
    if settings.promoted_3s_min_velocity_decay_ratio <= 0:
        raise ValueError("PROMOTED_3S_MIN_VELOCITY_DECAY_RATIO must be > 0")
    if settings.layer4_trigger_points <= 0:
        raise ValueError("LAYER4_TRIGGER_POINTS must be > 0")
    if settings.layer4_required_followthrough_points <= settings.layer4_trigger_points:
        raise ValueError("LAYER4_REQUIRED_FOLLOWTHROUGH_POINTS must be > LAYER4_TRIGGER_POINTS")
    if settings.layer4_window_seconds <= 0:
        raise ValueError("LAYER4_WINDOW_SECONDS must be > 0")

    if settings.enable_early_risk:
        if settings.early_risk_suspicion_seconds <= 0:
            raise ValueError("EARLY_RISK_SUSPICION_SECONDS must be > 0")
        if settings.early_risk_exit_seconds <= settings.early_risk_suspicion_seconds:
            raise ValueError(
                "EARLY_RISK_EXIT_SECONDS must be greater than EARLY_RISK_SUSPICION_SECONDS"
            )

    if settings.enable_path_risk:
        if settings.path_risk_check_seconds <= settings.early_risk_exit_seconds:
            raise ValueError("PATH_RISK_CHECK_SECONDS must be greater than EARLY_RISK_EXIT_SECONDS")

    if settings.enable_edge_invalidation:
        if settings.edge_invalidation_1s_check_seconds <= 0:
            raise ValueError("EDGE_INVALIDATION_1S_CHECK_SECONDS must be > 0")
        if settings.edge_invalidation_3s_check_seconds <= 0:
            raise ValueError("EDGE_INVALIDATION_3S_CHECK_SECONDS must be > 0")
        if (
            settings.edge_invalidation_1s_enabled
            and settings.edge_invalidation_3s_enabled
            and settings.edge_invalidation_3s_check_seconds <= settings.edge_invalidation_1s_check_seconds
        ):
            raise ValueError(
                "EDGE_INVALIDATION_3S_CHECK_SECONDS must be greater than EDGE_INVALIDATION_1S_CHECK_SECONDS"
            )
        if settings.edge_invalidation_1s_min_runup_points < 0:
            raise ValueError("EDGE_INVALIDATION_1S_MIN_RUNUP_POINTS must be >= 0")
        if settings.edge_invalidation_3s_min_runup_points < 0:
            raise ValueError("EDGE_INVALIDATION_3S_MIN_RUNUP_POINTS must be >= 0")
        if settings.edge_invalidation_3s_max_drawdown_points <= 0:
            raise ValueError("EDGE_INVALIDATION_3S_MAX_DRAWDOWN_POINTS must be > 0")
        if settings.edge_invalidation_3s_pinned_pnl_abs_points < 0:
            raise ValueError("EDGE_INVALIDATION_3S_PINNED_PNL_ABS_POINTS must be >= 0")
        if settings.edge_invalidation_hard_stop_enabled and settings.edge_invalidation_hard_stop_points <= 0:
            raise ValueError("EDGE_INVALIDATION_HARD_STOP_POINTS must be > 0")
        if settings.edge_invalidation_stale_quote_max_seconds <= 0:
            raise ValueError("EDGE_INVALIDATION_STALE_QUOTE_MAX_SECONDS must be > 0")

    if settings.enable_dynamic_risky_target:
        if settings.risky_target_points <= 0:
            raise ValueError("RISKY_TARGET_POINTS must be > 0 when ENABLE_DYNAMIC_RISKY_TARGET=true")
        if settings.strict_after_1pm_risky_target_points <= 0:
            raise ValueError(
                "STRICT_AFTER_1PM_RISKY_TARGET_POINTS must be > 0 when ENABLE_DYNAMIC_RISKY_TARGET=true"
            )

    if settings.post_exit_observation_interval_seconds <= 0:
        raise ValueError("POST_EXIT_OBSERVATION_INTERVAL_SECONDS must be > 0")
    if settings.enable_post_exit_observation and settings.post_exit_observation_seconds <= 0:
        raise ValueError("POST_EXIT_OBSERVATION_SECONDS must be > 0 when ENABLE_POST_EXIT_OBSERVATION=true")
    if not settings.enable_post_exit_observation and settings.post_exit_observation_seconds < 0:
        raise ValueError("POST_EXIT_OBSERVATION_SECONDS must be >= 0")
    if settings.target_reprice_debounce_seconds < 0:
        raise ValueError("TARGET_REPRICE_DEBOUNCE_SECONDS must be >= 0")
    if settings.sensex_tape_strike_range_points < 0:
        raise ValueError("SENSEX_TAPE_STRIKE_RANGE_POINTS must be >= 0")
    if settings.sensex_tape_strike_step_points <= 0:
        raise ValueError("SENSEX_TAPE_STRIKE_STEP_POINTS must be > 0")
    if settings.sensex_tape_rebase_on_atm_move_points <= 0:
        raise ValueError("SENSEX_TAPE_REBASE_ON_ATM_MOVE_POINTS must be > 0")
    if settings.sensex_tape_expiry_mode != "nearest":
        raise ValueError("SENSEX_TAPE_EXPIRY_MODE currently supports only: nearest")
    if settings.enable_sensex_option_tape_recorder and not (
        settings.sensex_tape_include_ce or settings.sensex_tape_include_pe
    ):
        raise ValueError(
            "At least one of SENSEX_TAPE_INCLUDE_CE or SENSEX_TAPE_INCLUDE_PE must be true when ENABLE_SENSEX_OPTION_TAPE_RECORDER=true"
        )
    if settings.stream_watchdog_max_idle_seconds <= 0:
        raise ValueError("STREAM_WATCHDOG_MAX_IDLE_SECONDS must be > 0")
    if settings.watchdog_hard_reconnect_seconds <= 0:
        raise ValueError("WATCHDOG_HARD_RECONNECT_SECONDS must be > 0")
    if settings.watchdog_hard_reconnect_seconds <= settings.stream_watchdog_max_idle_seconds:
        raise ValueError(
            "WATCHDOG_HARD_RECONNECT_SECONDS must be greater than STREAM_WATCHDOG_MAX_IDLE_SECONDS"
        )
    if settings.stream_reconnect_cooldown_seconds <= 0:
        raise ValueError("STREAM_RECONNECT_COOLDOWN_SECONDS must be > 0")
    if settings.stream_connect_timeout_seconds <= 0:
        raise ValueError("STREAM_CONNECT_TIMEOUT_SECONDS must be > 0")
    if settings.stream_first_tick_timeout_seconds <= 0:
        raise ValueError("STREAM_FIRST_TICK_TIMEOUT_SECONDS must be > 0")
    if settings.heartbeat_log_interval_seconds <= 0:
        raise ValueError("HEARTBEAT_LOG_INTERVAL_SECONDS must be > 0")
    if settings.rebase_persist_ticks <= 0:
        raise ValueError("REBASE_PERSIST_TICKS must be > 0")
    if settings.rebase_cooldown_seconds < 0:
        raise ValueError("REBASE_COOLDOWN_SECONDS must be >= 0")
    if settings.rebase_min_move_points <= 0:
        raise ValueError("REBASE_MIN_MOVE_POINTS must be > 0")
    if settings.critical_tick_queue_maxsize <= 0:
        raise ValueError("CRITICAL_TICK_QUEUE_MAXSIZE must be > 0")
    if settings.background_tick_queue_maxsize <= 0:
        raise ValueError("BACKGROUND_TICK_QUEUE_MAXSIZE must be > 0")
    if settings.journal_queue_maxsize <= 0:
        raise ValueError("JOURNAL_QUEUE_MAXSIZE must be > 0")
    if settings.journal_flush_interval_seconds <= 0:
        raise ValueError("JOURNAL_FLUSH_INTERVAL_SECONDS must be > 0")



def load_settings() -> Settings:
    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=repo_root / ".env")
    data_dir = _path_env("DATA_DIR", repo_root, repo_root)
    logs_dir = _path_env("LOGS_DIR", data_dir / "logs", data_dir)
    runtime_dir = _path_env("RUNTIME_DIR", data_dir / "runtime", data_dir)
    token_store_path = _path_env(
        "TOKEN_STORE_PATH",
        runtime_dir / "kite_access_token.json",
        runtime_dir,
    )
    settings = Settings(
        kite_api_key=_required("KITE_API_KEY"),
        kite_api_secret=_required("KITE_API_SECRET"),
        kite_access_token=os.getenv("KITE_ACCESS_TOKEN", "").strip(),
        kite_request_token=os.getenv("KITE_REQUEST_TOKEN", "").strip(),
        data_dir=data_dir,
        logs_dir=logs_dir,
        runtime_dir=runtime_dir,
        token_store_path=token_store_path,
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "2")),
        starting_capital=float(os.getenv("STARTING_CAPITAL", "1000000")),
        trade_qty=int(os.getenv("TRADE_QTY", "500")),
        order_product=os.getenv("ORDER_PRODUCT", "MIS").strip().upper(),
        trading_mode=os.getenv("TRADING_MODE", "paper").strip().lower(),
        position_sizing_mode=os.getenv("POSITION_SIZING_MODE", "fixed").strip().lower(),
        capital_budget=float(os.getenv("CAPITAL_BUDGET", "300000")),
        use_kite_funds=_bool("USE_KITE_FUNDS", "false"),
        target_points=float(os.getenv("TARGET_POINTS", "3")),
        entry_buffer_points=float(os.getenv("ENTRY_BUFFER_POINTS", "5")),
        call_offset_points=int(os.getenv("CALL_OFFSET_POINTS", "-200")),
        put_offset_points=int(os.getenv("PUT_OFFSET_POINTS", "200")),
        underlying_symbol=os.getenv("UNDERLYING_SYMBOL", "BSE:SENSEX"),
        instruments_cache_path=_path_env("INSTRUMENTS_CACHE_PATH", data_dir / "data" / "instruments.csv", data_dir),
        trade_log_path=_path_env("TRADE_LOG_PATH", logs_dir / "trades.jsonl", data_dir),
        event_log_path=_path_env("EVENT_LOG_PATH", logs_dir / "events.jsonl", data_dir),
        enriched_trade_log_path=_path_env(
            "ENRICHED_TRADE_LOG_PATH",
            logs_dir / "trades_enriched.jsonl",
            data_dir,
        ),
        features_output_path=_path_env("FEATURES_OUTPUT_PATH", logs_dir / "features_daily.csv", data_dir),
        control_path=_path_env("CONTROL_PATH", runtime_dir / "control.json", data_dir),
        entry_cutoff_time=os.getenv("ENTRY_CUTOFF_TIME", "14:55"),
        entry_window_seconds=int(os.getenv("ENTRY_WINDOW_SECONDS", "40")),
        entry_window_max_seconds=float(os.getenv("ENTRY_WINDOW_MAX_SECONDS", "10.0")),
        entry_feature_lookback_seconds=float(os.getenv("ENTRY_FEATURE_LOOKBACK_SECONDS", "5.0")),
        post_1pm_time_stop_seconds=int(os.getenv("POST_1PM_TIME_STOP_SECONDS", "60")),
        session_square_off_enabled=_bool("SESSION_SQUARE_OFF_ENABLED", "false"),
        session_square_off_time=os.getenv("SESSION_SQUARE_OFF_TIME", "15:15"),
        early_failure_window_seconds=int(os.getenv("EARLY_FAILURE_WINDOW_SECONDS", "15")),
        early_failure_mfe_min=float(os.getenv("EARLY_FAILURE_MFE_MIN", "1.5")),
        early_failure_mae_max=float(os.getenv("EARLY_FAILURE_MAE_MAX", "-1.5")),
        enable_verbose_trade_logging=_bool("ENABLE_VERBOSE_TRADE_LOGGING", "true"),
        enable_signal_logging=_bool("ENABLE_SIGNAL_LOGGING", "true"),
        enable_entry_context_logging=_bool("ENABLE_ENTRY_CONTEXT_LOGGING", "true"),
        enable_snapshot_logging=_bool("ENABLE_SNAPSHOT_LOGGING", "true"),
        enable_post_exit_observation=_bool("ENABLE_POST_EXIT_OBSERVATION", "true"),
        post_exit_observation_seconds=int(os.getenv("POST_EXIT_OBSERVATION_SECONDS", "15")),
        post_exit_observation_interval_seconds=int(
            os.getenv("POST_EXIT_OBSERVATION_INTERVAL_SECONDS", "1")
        ),
        snapshot_seconds=_int_list("SNAPSHOT_SECONDS", "1,3,5,10,15,20,30,60"),
        enable_hard_stop=_bool("ENABLE_HARD_STOP", "true"),
        hard_stop_arm_after_seconds=int(os.getenv("HARD_STOP_ARM_AFTER_SECONDS", "30")),
        hard_stop_points=float(os.getenv("HARD_STOP_POINTS", "8")),
        continuation_call_hard_stop_points=float(
            os.getenv("CONTINUATION_CALL_HARD_STOP_POINTS", "6")
        ),
        enable_microburst_gate=_bool("ENABLE_MICROBURST_GATE", "true"),
        microburst_min_score=int(os.getenv("MICROBURST_MIN_SCORE", "3")),
        microburst_ind_accel_threshold_1=float(
            os.getenv("MICROBURST_IND_ACCEL_THRESHOLD_1", "1.688")
        ),
        microburst_ind_accel_threshold_2=float(
            os.getenv("MICROBURST_IND_ACCEL_THRESHOLD_2", "3.945")
        ),
        microburst_opt_velocity_threshold=float(
            os.getenv("MICROBURST_OPT_VELOCITY_THRESHOLD", "1.583")
        ),
        microburst_opt_depth_imb_threshold=float(
            os.getenv("MICROBURST_OPT_DEPTH_IMB_THRESHOLD", "0.0857")
        ),
        microburst_ind_velocity_min=float(
            os.getenv("MICROBURST_IND_VELOCITY_MIN", "1.646")
        ),
        microburst_ind_velocity_max=float(
            os.getenv("MICROBURST_IND_VELOCITY_MAX", "2.356")
        ),
        normal_target_points=float(os.getenv("NORMAL_TARGET_POINTS", "3.0")),
        promoted_min_score=int(os.getenv("PROMOTED_MIN_SCORE", "5")),
        promoted_target_points=float(os.getenv("PROMOTED_TARGET_POINTS", "7.0")),
        promoted_3s_min_runup_points=float(
            os.getenv("PROMOTED_3S_MIN_RUNUP_POINTS", "4.0")
        ),
        promoted_3s_min_pnl_points=float(
            os.getenv("PROMOTED_3S_MIN_PNL_POINTS", "1.5")
        ),
        promoted_3s_max_mae_points=float(
            os.getenv("PROMOTED_3S_MAX_MAE_POINTS", "3.5")
        ),
        promoted_3s_min_velocity_decay_ratio=float(
            os.getenv("PROMOTED_3S_MIN_VELOCITY_DECAY_RATIO", "0.5")
        ),
        layer4_enabled=_bool("LAYER4_ENABLED", "true"),
        layer4_trigger_points=float(os.getenv("LAYER4_TRIGGER_POINTS", "3.0")),
        layer4_required_followthrough_points=float(
            os.getenv("LAYER4_REQUIRED_FOLLOWTHROUGH_POINTS", "4.5")
        ),
        layer4_window_seconds=float(os.getenv("LAYER4_WINDOW_SECONDS", "2.0")),
        enable_early_risk=_bool("ENABLE_EARLY_RISK", "true"),
        early_risk_suspicion_seconds=int(os.getenv("EARLY_RISK_SUSPICION_SECONDS", "5")),
        early_risk_exit_seconds=int(os.getenv("EARLY_RISK_EXIT_SECONDS", "10")),
        early_risk_runup_max_for_exit=float(os.getenv("EARLY_RISK_RUNUP_MAX_FOR_EXIT", "1.0")),
        early_risk_drawdown_min_for_exit=float(
            os.getenv("EARLY_RISK_DRAWDOWN_MIN_FOR_EXIT", "-3.0")
        ),
        early_risk_require_below_entry=_bool("EARLY_RISK_REQUIRE_BELOW_ENTRY", "true"),
        early_risk_suspicion_current_pnl=float(
            os.getenv("EARLY_RISK_SUSPICION_CURRENT_PNL", "-2.0")
        ),
        early_risk_suspicion_require_adverse_first_move=_bool(
            "EARLY_RISK_SUSPICION_REQUIRE_ADVERSE_FIRST_MOVE", "false"
        ),
        early_risk_strict_after_1pm=_bool("EARLY_RISK_STRICT_AFTER_1PM", "true"),
        enable_path_risk=_bool("ENABLE_PATH_RISK", "true"),
        path_risk_check_seconds=int(os.getenv("PATH_RISK_CHECK_SECONDS", "30")),
        path_risk_pnl_min_for_exit=float(os.getenv("PATH_RISK_PNL_MIN_FOR_EXIT", "-6.0")),
        path_risk_runup_max_for_exit=float(os.getenv("PATH_RISK_RUNUP_MAX_FOR_EXIT", "2.0")),
        path_risk_strict_after_1pm=_bool("PATH_RISK_STRICT_AFTER_1PM", "true"),
        path_risk_tighten_if_fragile=_bool("PATH_RISK_TIGHTEN_IF_FRAGILE", "true"),
        enable_edge_invalidation=_bool("ENABLE_EDGE_INVALIDATION", "true"),
        edge_invalidation_1s_enabled=_bool("EDGE_INVALIDATION_1S_ENABLED", "true"),
        edge_invalidation_3s_enabled=_bool("EDGE_INVALIDATION_3S_ENABLED", "true"),
        edge_invalidation_1s_check_seconds=float(
            os.getenv("EDGE_INVALIDATION_1S_CHECK_SECONDS", "1.0")
        ),
        edge_invalidation_3s_check_seconds=float(
            os.getenv("EDGE_INVALIDATION_3S_CHECK_SECONDS", "3.0")
        ),
        edge_invalidation_1s_min_runup_points=float(
            os.getenv("EDGE_INVALIDATION_1S_MIN_RUNUP_POINTS", "1.0")
        ),
        edge_invalidation_1s_max_pnl_points=float(
            os.getenv("EDGE_INVALIDATION_1S_MAX_PNL_POINTS", "0.0")
        ),
        edge_invalidation_3s_min_runup_points=float(
            os.getenv("EDGE_INVALIDATION_3S_MIN_RUNUP_POINTS", "2.0")
        ),
        edge_invalidation_3s_max_drawdown_points=float(
            os.getenv("EDGE_INVALIDATION_3S_MAX_DRAWDOWN_POINTS", "4.0")
        ),
        edge_invalidation_3s_pinned_pnl_abs_points=float(
            os.getenv("EDGE_INVALIDATION_3S_PINNED_PNL_ABS_POINTS", "1.0")
        ),
        edge_invalidation_hard_stop_points=float(
            os.getenv("EDGE_INVALIDATION_HARD_STOP_POINTS", "6.0")
        ),
        edge_invalidation_hard_stop_enabled=_bool(
            "EDGE_INVALIDATION_HARD_STOP_ENABLED", "true"
        ),
        edge_invalidation_stale_quote_max_seconds=float(
            os.getenv("EDGE_INVALIDATION_STALE_QUOTE_MAX_SECONDS", "1.5")
        ),
        edge_invalidation_kill_on_stale_quotes=_bool(
            "EDGE_INVALIDATION_KILL_ON_STALE_QUOTES", "false"
        ),
        edge_invalidation_require_subsecond_precision=_bool(
            "EDGE_INVALIDATION_REQUIRE_SUBSECOND_PRECISION", "false"
        ),
        edge_invalidation_use_underlying_confirmation=_bool(
            "EDGE_INVALIDATION_USE_UNDERLYING_CONFIRMATION", "false"
        ),
        edge_invalidation_use_spread_filter=_bool(
            "EDGE_INVALIDATION_USE_SPREAD_FILTER", "false"
        ),
        prefer_edge_invalidation_over_legacy_early_risk=_bool(
            "PREFER_EDGE_INVALIDATION_OVER_LEGACY_EARLY_RISK", "true"
        ),
        enable_dynamic_risky_target=_bool("ENABLE_DYNAMIC_RISKY_TARGET", "true"),
        risky_target_points=float(os.getenv("RISKY_TARGET_POINTS", "2.0")),
        strict_after_1pm_risky_target_points=float(
            os.getenv("STRICT_AFTER_1PM_RISKY_TARGET_POINTS", "2.0")
        ),
        enable_order_timeline_logging=_bool("ENABLE_ORDER_TIMELINE_LOGGING", "true"),
        enable_quote_logging=_bool("ENABLE_QUOTE_LOGGING", "true"),
        enable_velocity_logging=_bool("ENABLE_VELOCITY_LOGGING", "true"),
        enable_post_exit_counterfactual=_bool("ENABLE_POST_EXIT_COUNTERFACTUAL", "true"),
        enable_exit_decision_logging=_bool("ENABLE_EXIT_DECISION_LOGGING", "true"),
        enable_target_reprice_modify=_bool("ENABLE_TARGET_REPRICE_MODIFY", "true"),
        enable_target_reprice_fallback_cancel_replace=_bool(
            "ENABLE_TARGET_REPRICE_FALLBACK_CANCEL_REPLACE", "true"
        ),
        enable_slippage_logging=_bool("ENABLE_SLIPPAGE_LOGGING", "true"),
        target_reprice_debounce_seconds=int(os.getenv("TARGET_REPRICE_DEBOUNCE_SECONDS", "2")),
        enable_full_option_tape_logging=_bool("ENABLE_FULL_OPTION_TAPE_LOGGING", "false"),
        enable_sensex_option_tape_recorder=_bool("ENABLE_SENSEX_OPTION_TAPE_RECORDER", "false"),
        sensex_tape_strike_range_points=int(os.getenv("SENSEX_TAPE_STRIKE_RANGE_POINTS", "1500")),
        sensex_tape_strike_step_points=int(os.getenv("SENSEX_TAPE_STRIKE_STEP_POINTS", "100")),
        sensex_tape_expiry_mode=os.getenv("SENSEX_TAPE_EXPIRY_MODE", "nearest").strip().lower(),
        sensex_tape_include_ce=_bool("SENSEX_TAPE_INCLUDE_CE", "true"),
        sensex_tape_include_pe=_bool("SENSEX_TAPE_INCLUDE_PE", "true"),
        sensex_tape_rebase_on_atm_move_points=int(
            os.getenv("SENSEX_TAPE_REBASE_ON_ATM_MOVE_POINTS", "100")
        ),
        sensex_tape_log_dir=_path_env(
            "SENSEX_TAPE_LOG_DIR",
            data_dir / "data" / "tape" / "sensex_options",
            data_dir,
        ),
        sensex_tape_write_legacy_options_log=_bool(
            "SENSEX_TAPE_WRITE_LEGACY_OPTIONS_LOG", "true"
        ),
        stream_watchdog_max_idle_seconds=int(os.getenv("STREAM_WATCHDOG_MAX_IDLE_SECONDS", "5")),
        watchdog_hard_reconnect_seconds=int(os.getenv("WATCHDOG_HARD_RECONNECT_SECONDS", "8")),
        stream_reconnect_cooldown_seconds=int(os.getenv("STREAM_RECONNECT_COOLDOWN_SECONDS", "10")),
        stream_connect_timeout_seconds=int(os.getenv("STREAM_CONNECT_TIMEOUT_SECONDS", "10")),
        stream_first_tick_timeout_seconds=int(os.getenv("STREAM_FIRST_TICK_TIMEOUT_SECONDS", "8")),
        heartbeat_log_interval_seconds=int(os.getenv("HEARTBEAT_LOG_INTERVAL_SECONDS", "30")),
        rebase_persist_ticks=int(os.getenv("REBASE_PERSIST_TICKS", "3")),
        rebase_cooldown_seconds=int(os.getenv("REBASE_COOLDOWN_SECONDS", "3")),
        rebase_min_move_points=int(os.getenv("REBASE_MIN_MOVE_POINTS", "100")),
        critical_tick_queue_maxsize=int(os.getenv("CRITICAL_TICK_QUEUE_MAXSIZE", "5000")),
        background_tick_queue_maxsize=int(os.getenv("BACKGROUND_TICK_QUEUE_MAXSIZE", "20000")),
        journal_queue_maxsize=int(os.getenv("JOURNAL_QUEUE_MAXSIZE", "50000")),
        journal_flush_interval_seconds=int(os.getenv("JOURNAL_FLUSH_INTERVAL_SECONDS", "1")),
        write_daily_features=_bool("WRITE_DAILY_FEATURES", "true"),
        write_daily_policy_simulation=_bool("WRITE_DAILY_POLICY_SIMULATION", "false"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
    _validate(settings)
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return settings
