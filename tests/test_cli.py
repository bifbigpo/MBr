import shutil
from pathlib import Path

from mbr.cli import main

ROOT = Path(__file__).parent.parent


def test_calc(capsys):
    assert main(["calc", "free_bet_snr", "10", "5.0", "5.2"]) == 0
    out = capsys.readouterr().out
    assert "£7.72" in out and "76%" in out


def test_scan_from_fixture(tmp_path, monkeypatch, capsys):
    shutil.copytree(ROOT / "data", tmp_path / "data")
    shutil.copy(tmp_path / "data" / "offers.example.json", tmp_path / "data" / "offers.json")
    monkeypatch.chdir(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "epl_odds.json"
    assert main(["scan", "--fixture", str(fixture), "--now", "2026-10-30T12:00:00+00:00"]) == 0
    out = capsys.readouterr().out
    assert "hills-bet10-get30 · William Hill · qualifier £10" in out
    assert "skybet-free-bet-5 · Sky Bet · free bet SNR £5" in out
    assert "Arsenal v Tottenham Hotspur" in out


def test_scan_without_offers_file_explains(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["scan"]) == 1
    assert "offers.example.json" in capsys.readouterr().err
