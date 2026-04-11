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
    post_1pm_time_stop_seconds: int
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
    if settings.post_1pm_time_stop_seconds <= 0:
        raise ValueError("POST_1PM_TIME_STOP_SECONDS must be > 0")

    if settings.enable_hard_stop:
        if settings.hard_stop_points <= 0:
            raise ValueError("HARD_STOP_POINTS must be > 0 when ENABLE_HARD_STOP=true")
        if settings.continuation_call_hard_stop_points <= 0:
            raise ValueError(
                "CONTINUATION_CALL_HARD_STOP_POINTS must be > 0 when ENABLE_HARD_STOP=true"
            )
    if settings.hard_stop_arm_after_seconds < 0:
        raise ValueError("HARD_STOP_ARM_AFTER_SECONDS must be >= 0")

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
    settings = Settings(
        kite_api_key=_required("KITE_API_KEY"),
        kite_api_secret=os.getenv("KITE_API_SECRET", "").strip(),
        kite_access_token=_required("KITE_ACCESS_TOKEN"),
        kite_request_token=os.getenv("KITE_REQUEST_TOKEN", "").strip(),
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
        instruments_cache_path=Path(os.getenv("INSTRUMENTS_CACHE_PATH", "data/instruments.csv")),
        trade_log_path=Path(os.getenv("TRADE_LOG_PATH", "logs/trades.jsonl")),
        event_log_path=Path(os.getenv("EVENT_LOG_PATH", "logs/events.jsonl")),
        enriched_trade_log_path=Path(
            os.getenv("ENRICHED_TRADE_LOG_PATH", "logs/trades_enriched.jsonl")
        ),
        features_output_path=Path(os.getenv("FEATURES_OUTPUT_PATH", "logs/features_daily.csv")),
        control_path=Path(os.getenv("CONTROL_PATH", "runtime/control.json")),
        entry_cutoff_time=os.getenv("ENTRY_CUTOFF_TIME", "14:55"),
        entry_window_seconds=int(os.getenv("ENTRY_WINDOW_SECONDS", "40")),
        post_1pm_time_stop_seconds=int(os.getenv("POST_1PM_TIME_STOP_SECONDS", "60")),
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
