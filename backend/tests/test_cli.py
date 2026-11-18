from paddle_finder.cli.app import PaddleFinderApp
from paddle_finder.data import seed
from paddle_finder.data.schema import count_paddles, make_engine


def run_cli(catalog, answers, monkeypatch, capsys, tmp_path):
    replies = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(replies))
    monkeypatch.chdir(tmp_path)
    PaddleFinderApp(catalog).run()
    return capsys.readouterr().out


def test_terminal_app_preset_lookup_compare_and_summary(catalog, monkeypatch, capsys, tmp_path):
    out = run_cli(catalog, [
        "2", "1", "",                          # Power banger preset, no budget
        "3", "joola perseus",                  # look up
        "4", "jelly bean 2 hurache", "selkirk vanguard", "1", "",   # compare two paddles
        "5",                                   # dataset summary
        "q",
    ], monkeypatch, capsys, tmp_path)
    assert "TOP 10 PADDLES FOR YOU" in out
    assert "*** JOOLA Perseus" in out
    assert "Paddles by type (most common first):" in out
    exported = (tmp_path / "recommendations.csv").read_text()
    assert exported.startswith("Rank,Brand,Paddle,Match %")
    assert "Discount" not in exported and "discount" not in out.lower()


def test_terminal_questionnaire(catalog, monkeypatch, capsys, tmp_path):
    out = run_cli(catalog, ["1", "250", "y", "0", "0", "0",
                            "m", "4", "h", "5", "", "", "", "", "", "", "", "", "6"],
                  monkeypatch, capsys, tmp_path)
    assert "paddles passed your filters" in out and "TOP 10" in out


def test_seed_command_is_idempotent(tmp_path, capsys):
    url = "sqlite:///" + str(tmp_path / "seeded.db")
    assert seed.main(["--database-url", url]) == 0
    assert seed.main(["--database-url", url, "--if-empty"]) == 0
    assert "skipping" in capsys.readouterr().out
    assert count_paddles(make_engine(url)) == 494
