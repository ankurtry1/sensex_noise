from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_prod_compose_runs_services_as_configured_app_user() -> None:
    text = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert 'user: "${APP_UID:-1000}:${APP_GID:-1000}"' in text
    assert text.count('user: "${APP_UID:-1000}:${APP_GID:-1000}"') == 2
    assert "127.0.0.1:8000:8000" in text


def test_market_worker_timers_use_expected_schedule() -> None:
    start_timer = (ROOT / "deploy/systemd/sensex-market-worker.timer").read_text(encoding="utf-8")
    stop_timer = (ROOT / "deploy/systemd/sensex-market-worker-stop.timer").read_text(encoding="utf-8")

    assert "OnCalendar=Mon..Fri *-*-* 09:14:00" in start_timer
    assert "OnCalendar=Mon..Fri *-*-* 15:35:00" in stop_timer


def test_worker_command_dispatcher_assets_are_installed_by_timer_script() -> None:
    script = (ROOT / "deploy/scripts/install_market_worker_timers.sh").read_text(encoding="utf-8")
    service = (ROOT / "deploy/systemd/sensex-worker-command.service").read_text(encoding="utf-8")
    path_unit = (ROOT / "deploy/systemd/sensex-worker-command.path").read_text(encoding="utf-8")

    assert "sensex-worker-command.service" in script
    assert "sensex-worker-command.path" in script
    assert "--enable-controls" in script
    assert "worker_command_dispatch.sh" in service
    assert "PathExistsGlob=/var/lib/sensex-noise/runtime/commands/*.request" in path_unit


def test_fix_data_permissions_reports_app_uid_gid() -> None:
    script = (ROOT / "deploy/scripts/fix_data_permissions.sh").read_text(encoding="utf-8")

    assert "APP_UID=$(id -u" in script
    assert "APP_GID=$(id -g" in script
    assert "kite_access_token.json" in script
