"""
Integration tests for CLI Mascot functionality.
"""

import pytest
import os
import subprocess
import sys


class TestCLIStartupScreen:
    """Test bare `aios` command shows startup screen."""

    def test_aios_bare_command_shows_startup(self):
        """Running `aios` without args shows startup screen."""
        # Set environment for JSON mode to avoid TTY issues in CI
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        # Should exit cleanly
        assert result.returncode == 0

        # In JSON mode, startup screen is empty (no visual)
        # But command should still run
        assert result.stdout == ""

    def test_aios_version_flag(self):
        """Running `aios --version` shows version."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "--version"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        assert "AI-OS" in result.stdout
        assert "v" in result.stdout

    def test_aios_version_subcommand(self):
        """Running `aios version` shows version."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "version"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        assert "AI-OS" in result.stdout


class TestCLIStatusCommand:
    """Test `aios status` command."""

    def test_status_command_exists(self):
        """Status command is registered."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "status", "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        assert "status" in result.stdout.lower()

    def test_status_json_output(self):
        """Status command supports --json flag."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "status", "--json"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        # Should produce valid JSON
        assert result.returncode == 0
        import json
        try:
            data = json.loads(result.stdout.strip())
            assert "status" in data
            assert "health" in data
            assert "kernel" in data
        except json.JSONDecodeError:
            pytest.fail(f"Output is not valid JSON: {result.stdout}")


class TestCLIHealthCommand:
    """Test `aios health` command."""

    def test_health_command_exists(self):
        """Health command is registered."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "health", "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        assert "health" in result.stdout.lower()

    def test_health_json_output(self):
        """Health command supports --json flag."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "health", "--json"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        import json
        try:
            data = json.loads(result.stdout.strip())
            assert "status" in data
            assert "checks" in data
        except json.JSONDecodeError:
            pytest.fail(f"Output is not valid JSON: {result.stdout}")


class TestCLIReadyCommand:
    """Test `aios ready` command."""

    def test_ready_command_exists(self):
        """Ready command is registered."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "ready", "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        assert "ready" in result.stdout.lower()

    def test_ready_json_output(self):
        """Ready command supports --json flag."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "ready", "--json"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        import json
        try:
            data = json.loads(result.stdout.strip())
            assert "ready" in data
            assert "details" in data
        except json.JSONDecodeError:
            pytest.fail(f"Output is not valid JSON: {result.stdout}")


class TestCLIDiagnosticsCommand:
    """Test `aios diagnostics` command."""

    def test_diagnostics_command_exists(self):
        """Diagnostics command is registered."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "diagnostics", "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        assert "diagnostics" in result.stdout.lower()

    def test_diagnostics_json_output(self):
        """Diagnostics command supports --json flag."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "diagnostics", "--json"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        import json
        try:
            data = json.loads(result.stdout.strip())
            assert "lifecycle" in data
            assert "health" in data
        except json.JSONDecodeError:
            pytest.fail(f"Output is not valid JSON: {result.stdout}")


class TestCLIPreservedCommands:
    """Test that existing commands are preserved."""

    def test_doctor_command_preserved(self):
        """aios doctor command still works."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "doctor", "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        assert "doctor" in result.stdout.lower()

    def test_onboard_command_preserved(self):
        """aios onboard command still works."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "onboard", "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        assert "onboard" in result.stdout.lower()

    def test_kernel_subcommands_preserved(self):
        """aios kernel subcommands still work."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "kernel", "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        assert "kernel" in result.stdout.lower()


class TestCLIOutputModes:
    """Test output mode handling."""

    def test_json_mode_no_ansi(self):
        """JSON mode produces no ANSI escape sequences."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "status", "--json"],
            capture_output=True,
            text=True,
            env=env,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        # No ANSI escape sequences
        assert "\x1b[" not in result.stdout

    def test_json_mode_valid_json(self):
        """JSON mode produces valid JSON for all commands."""
        env = os.environ.copy()
        env["AIOS_JSON_OUTPUT"] = "1"

        commands = [
            ["status", "--json"],
            ["health", "--json"],
            ["ready", "--json"],
            ["diagnostics", "--json"],
        ]

        import json
        for cmd in commands:
            result = subprocess.run(
                [sys.executable, "-m", "aios.cli.main"] + cmd,
                capture_output=True,
                text=True,
                env=env,
                cwd="C:\\Development\\AI-OS",
                timeout=10,
            )
            assert result.returncode == 0, f"Command {cmd} failed: {result.stderr}"
            try:
                json.loads(result.stdout.strip())
            except json.JSONDecodeError as e:
                pytest.fail(f"Command {cmd} output not valid JSON: {e}\nOutput: {result.stdout}")


class TestTerminalCapabilityDetection:
    """Test terminal capability detection behavior."""

    def test_non_tty_detection(self):
        """Non-TTY output uses fallback mode."""
        # Run without TTY (piped)
        result = subprocess.run(
            [sys.executable, "-m", "aios.cli.main", "status", "--json"],
            capture_output=True,
            text=True,
            cwd="C:\\Development\\AI-OS",
            timeout=10,
        )

        assert result.returncode == 0
        # Should still produce valid JSON in non-TTY
        import json
        data = json.loads(result.stdout.strip())
        assert "status" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])