from __future__ import annotations

from click.testing import CliRunner

from call_intel.cli import cli


def test_should_show_multilingual_model_examples_in_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["process", "--help"])
    assert result.exit_code == 0
    assert ".en" not in result.output
