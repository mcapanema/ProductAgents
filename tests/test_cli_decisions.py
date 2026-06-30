"""Tests for the `productagents decisions export` CLI command."""

from productagents.app import cli


class _FakeReadService:
    def __init__(self, counts=(2, 1)):
        self._counts = counts
        self.called_with = None

    async def export(self, directory):
        self.called_with = directory
        return self._counts


async def test_decisions_export_reports_counts(tmp_path, capsys):
    service = _FakeReadService((2, 1))
    code = await cli.decisions_export(str(tmp_path), service=service)
    assert code == 0
    assert service.called_with == str(tmp_path)
    out = capsys.readouterr().out
    assert "2 decision(s)" in out
    assert "1 outcome(s)" in out
