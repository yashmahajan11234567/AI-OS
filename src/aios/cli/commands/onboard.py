"""
CLI Commands for User Resource Onboarding (Phase: USER RESOURCE ONBOARDING Layer).

Provides `aios onboard` subcommands to:
- List all integrations with current state
- Validate resources for one or all integrations
- Attempt REAL connections (gated)
- Run health checks
- Get status reports for dashboard
- Enable/disable REAL mode (with confirmation)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from aios.integrations import (
    load_integrations_config,
    IntegrationConfigRegistry,
    IntegrationMode,
    CANONICAL_INTEGRATIONS,
    assert_real_allowed,
    ValidationRegistry,
)
from aios.integrations.state import IntegrationState


def _print_error(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _print_warning(msg: str) -> None:
    print(f"WARNING: {msg}", file=sys.stderr)


def _print_info(msg: str) -> None:
    print(f"INFO: {msg}")


def _get_registry() -> IntegrationConfigRegistry:
    """Load the integration config registry."""
    return load_integrations_config()


def _get_validation_registry() -> ValidationRegistry:
    """Get a validation registry instance."""
    return ValidationRegistry()


def cmd_list(args: list[str]) -> int:
    """List all integrations with current state."""
    registry = _get_registry()
    validation_registry = _get_validation_registry()

    print(f"{'INTEGRATION':<25} {'MODE':<8} {'STATE':<22} {'REAL_ALLOWED':<14} {'RESOURCE':<10} {'NOTES'}")
    print("-" * 110)

    for name in CANONICAL_INTEGRATIONS:
        entry = registry.get(name)
        if not entry:
            continue

        report = entry.get_status_report()
        notes = entry.notes[:50] if entry.notes else ""

        print(f"{name:<25} {report.mode:<8} {report.state.value:<22} {str(report.real_allowed):<14} "
              f"{str(report.user_resource_present):<10} {notes}")

    return 0


def cmd_validate(args: list[str]) -> int:
    """Validate resources for an integration or all integrations."""
    import argparse
    parser = argparse.ArgumentParser(prog="aios onboard validate")
    parser.add_argument("integration", nargs="?", help="Integration name (or 'all')")
    parser.add_argument("--all", action="store_true", help="Validate all integrations")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parsed = parser.parse_args(args)

    validation_registry = _get_validation_registry()

    if parsed.all or parsed.integration == "all":
        results = validation_registry.validate_all()
        if parsed.json:
            output = {name: r.provenance.get("validated_at", datetime.now().isoformat()) for name, r in results.items()}
            json.dump({name: {"state": r.state.value, "passed": r.passed, "errors": r.errors, "warnings": r.warnings,
                              "details": r.details} for name, r in results.items()}, sys.stdout, indent=2)
            print()
            return 0

        print(f"{'INTEGRATION':<25} {'STATE':<22} {'PASSED':<8} {'ERRORS'}")
        print("-" * 90)
        for name, result in results.items():
            errors_str = "; ".join(result.errors) if result.errors else ""
            warnings_str = "; ".join(result.warnings) if result.warnings else ""
            details = f"{errors_str} {warnings_str}".strip()
            print(f"{name:<25} {result.state.value:<22} {str(result.passed):<8} {details}")
        return 0

    if not parsed.integration:
        _print_error("Integration name required (or use --all)")
        return 1

    if parsed.integration not in CANONICAL_INTEGRATIONS:
        _print_error(f"Unknown integration: {parsed.integration}. Valid: {', '.join(CANONICAL_INTEGRATIONS)}")
        return 1

    result = validation_registry.validate(parsed.integration)
    if parsed.json:
        json.dump({"state": result.state.value, "passed": result.passed, "errors": result.errors,
                   "warnings": result.warnings, "details": result.details}, sys.stdout, indent=2)
        print()
        return 0

    print(f"Integration: {parsed.integration}")
    print(f"State:       {result.state.value}")
    print(f"Passed:      {result.passed}")
    if result.details:
        print(f"Details:     {json.dumps(result.details, indent=12)}")
    if result.errors:
        print("Errors:")
        for e in result.errors:
            print(f"  - {e}")
    if result.warnings:
        print("Warnings:")
        for w in result.warnings:
            print(f"  - {w}")

    return 0 if result.passed else 1


def cmd_connect(args: list[str]) -> int:
    """Attempt REAL connection for an integration (requires env gate + validation)."""
    import argparse
    parser = argparse.ArgumentParser(prog="aios onboard connect")
    parser.add_argument("integration", help="Integration name")
    parser.add_argument("--confirm", action="store_true", help="Confirm REAL connection attempt")
    parsed = parser.parse_args(args)

    if parsed.integration not in CANONICAL_INTEGRATIONS:
        _print_error(f"Unknown integration: {parsed.integration}")
        return 1

    if not parsed.confirm:
        _print_error("REAL connection requires --confirm flag")
        return 1

    registry = _get_registry()
    entry = registry.get(parsed.integration)
    if not entry:
        _print_error(f"Integration not configured: {parsed.integration}")
        return 1

    # Check env gate
    if entry.real_gated and os.environ.get("AIOS_REAL_INTEGRATION_ENABLED", "").lower() not in ("1", "true", "yes", "on"):
        _print_error("REAL connection blocked: AIOS_REAL_INTEGRATION_ENABLED not set")
        print("Set AIOS_REAL_INTEGRATION_ENABLED=1 to enable REAL mode operations")
        return 1

    # Check validation state
    if entry.state != IntegrationState.VALIDATED:
        _print_error(f"Integration not validated. Current state: {entry.state.value}. Run 'aios onboard validate {parsed.integration}' first.")
        return 1

    if not entry.real_allowed():
        _print_error("REAL connection not permitted. Check mode, env gate, and user resource.")
        return 1

    # Delegate to actual adapter/MCPManager
    _print_info(f"Attempting REAL connection for {parsed.integration}...")
    result = entry.attempt_connection()

    if result.connected:
        print(f"SUCCESS: {parsed.integration} connected (state: {result.state.value})")
        if result.details:
            print(f"Details: {json.dumps(result.details, indent=2)}")
        return 0
    else:
        _print_error(f"Connection failed: {result.errors}")
        return 1


def cmd_health(args: list[str]) -> int:
    """Run health check for an integration."""
    import argparse
    parser = argparse.ArgumentParser(prog="aios onboard health")
    parser.add_argument("integration", help="Integration name")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parsed = parser.parse_args(args)

    if parsed.integration not in CANONICAL_INTEGRATIONS:
        _print_error(f"Unknown integration: {parsed.integration}")
        return 1

    registry = _get_registry()
    entry = registry.get(parsed.integration)
    if not entry:
        _print_error(f"Integration not configured: {parsed.integration}")
        return 1

    result = entry.run_health_check()

    if parsed.json:
        json.dump({"state": result.state.value, "healthy": result.healthy,
                   "errors": result.errors, "details": result.details}, sys.stdout, indent=2)
        print()
        return 0

    print(f"Integration:   {parsed.integration}")
    print(f"State:         {result.state.value}")
    print(f"Healthy:       {result.healthy}")
    if result.details:
        print(f"Details:       {json.dumps(result.details, indent=12)}")
    if result.errors:
        print("Errors:")
        for e in result.errors:
            print(f"  - {e}")

    return 0 if result.healthy else 1


def cmd_status(args: list[str]) -> int:
    """Get full status report for dashboard (all integrations)."""
    import argparse
    parser = argparse.ArgumentParser(prog="aios onboard status")
    parser.add_argument("--json", action="store_true", help="Output as JSON (machine-readable)")
    parser.add_argument("--integration", help="Single integration status")
    parsed = parser.parse_args(args)

    validation_registry = _get_validation_registry()

    if parsed.integration:
        if parsed.integration not in CANONICAL_INTEGRATIONS:
            _print_error(f"Unknown integration: {parsed.integration}")
            return 1
        reports = {parsed.integration: validation_registry.get(parsed.integration).validate(parsed.integration)}
        # Better: use the config entry's get_status_report
        registry = _get_registry()
        entry = registry.get(parsed.integration)
        if entry:
            report = entry.get_status_report()
            if parsed.json:
                json.dump(report.to_dict(), sys.stdout, indent=2)
                print()
            else:
                print(json.dumps(report.to_dict(), indent=2))
            return 0
        _print_error(f"Integration not configured: {parsed.integration}")
        return 1

    reports = validation_registry.get_status_reports()

    if parsed.json:
        json.dump({name: r.to_dict() for name, r in reports.items()}, sys.stdout, indent=2)
        print()
        return 0

    print("INTEGRATION STATUS REPORT")
    print("=" * 80)
    for name, report in reports.items():
        print(f"\n--- {name} ---")
        print(f"  State:              {report.state.value}")
        print(f"  Mode:               {report.mode}")
        print(f"  Real Allowed:       {report.real_allowed}")
        print(f"  User Resource:      {report.user_resource_present}")
        print(f"  Real Gated:         {report.real_gated}")
        print(f"  Requires Resource:  {report.requires_user_resource}")
        if report.last_validated:
            print(f"  Last Validated:     {report.last_validated.isoformat()}")
        if report.last_health_check:
            print(f"  Last Health Check:  {report.last_health_check.isoformat()}")
        if report.errors:
            print(f"  Errors:             {report.errors}")
        if report.warnings:
            print(f"  Warnings:           {report.warnings}")

    return 0


def cmd_enable(args: list[str]) -> int:
    """Enable REAL mode for an integration (writes to integrations.yaml)."""
    import argparse
    import yaml
    parser = argparse.ArgumentParser(prog="aios onboard enable")
    parser.add_argument("integration", help="Integration name")
    parser.add_argument("--confirm", action="store_true", required=True, help="Confirm mode change to REAL")
    parsed = parser.parse_args(args)

    if parsed.integration not in CANONICAL_INTEGRATIONS:
        _print_error(f"Unknown integration: {parsed.integration}")
        return 1

    config_path = Path("config/integrations.yaml")
    data: dict[str, Any] = {}
    if config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text()) or {}
        except Exception:
            data = {}

    integrations = data.get("integrations", {})
    if parsed.integration not in integrations:
        integrations[parsed.integration] = {}

    integrations[parsed.integration]["mode"] = "real"
    data["integrations"] = integrations

    config_path.write_text(yaml.dump(data, sort_keys=False))
    _print_info(f"Set {parsed.integration} mode: real in {config_path}")
    _print_warning("Remember: REAL mode still requires AIOS_REAL_INTEGRATION_ENABLED=1 and user resource present")
    return 0


def cmd_disable(args: list[str]) -> int:
    """Disable REAL mode for an integration (set to mock)."""
    import argparse
    import yaml
    parser = argparse.ArgumentParser(prog="aios onboard disable")
    parser.add_argument("integration", help="Integration name")
    parsed = parser.parse_args(args)

    if parsed.integration not in CANONICAL_INTEGRATIONS:
        _print_error(f"Unknown integration: {parsed.integration}")
        return 1

    config_path = Path("config/integrations.yaml")
    data: dict[str, Any] = {}
    if config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text()) or {}
        except Exception:
            data = {}

    integrations = data.get("integrations", {})
    if parsed.integration not in integrations:
        integrations[parsed.integration] = {}

    integrations[parsed.integration]["mode"] = "mock"
    data["integrations"] = integrations

    config_path.write_text(yaml.dump(data, sort_keys=False))
    _print_info(f"Set {parsed.integration} mode: mock in {config_path}")
    return 0


def main(args: list[str]) -> int:
    """Main entry point for `aios onboard` command."""
    import argparse
    parser = argparse.ArgumentParser(prog="aios onboard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List all integrations with current state")

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate resources for integration(s)")
    p_validate.add_argument("integration", nargs="?", help="Integration name (or 'all')")
    p_validate.add_argument("--all", action="store_true", help="Validate all")
    p_validate.add_argument("--json", action="store_true", help="JSON output")

    # connect
    p_connect = subparsers.add_parser("connect", help="Attempt REAL connection (gated)")
    p_connect.add_argument("integration", help="Integration name")
    p_connect.add_argument("--confirm", action="store_true", required=True, help="Confirm REAL attempt")

    # health
    p_health = subparsers.add_parser("health", help="Run health check")
    p_health.add_argument("integration", help="Integration name")
    p_health.add_argument("--json", action="store_true", help="JSON output")

    # status
    p_status = subparsers.add_parser("status", help="Full status report for dashboard")
    p_status.add_argument("--json", action="store_true", help="JSON output")
    p_status.add_argument("--integration", help="Single integration")

    # enable
    p_enable = subparsers.add_parser("enable", help="Enable REAL mode (writes config)")
    p_enable.add_argument("integration", help="Integration name")
    p_enable.add_argument("--confirm", action="store_true", required=True, help="Confirm")

    # disable
    p_disable = subparsers.add_parser("disable", help="Disable REAL mode (set mock)")
    p_disable.add_argument("integration", help="Integration name")

    parsed = parser.parse_args(args)

    if parsed.command == "list":
        return cmd_list([])
    elif parsed.command == "validate":
        return cmd_validate(sys.argv[3:])  # Pass remaining args
    elif parsed.command == "connect":
        return cmd_connect(sys.argv[3:])
    elif parsed.command == "health":
        return cmd_health(sys.argv[3:])
    elif parsed.command == "status":
        return cmd_status(sys.argv[3:])
    elif parsed.command == "enable":
        return cmd_enable(sys.argv[3:])
    elif parsed.command == "disable":
        return cmd_disable(sys.argv[3:])

    _print_error(f"Unknown command: {parsed.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))