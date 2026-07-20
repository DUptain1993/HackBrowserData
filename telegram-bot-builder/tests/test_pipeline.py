"""Offline pipeline: digest -> heuristic analysis -> generation."""

import os

from botbuilder import analyzer, generator, repo

EXAMPLE = os.path.join(os.path.dirname(__file__), "..", "examples", "hello-cli")


def test_digest_detects_language_and_entry_point():
    digest = repo.build_digest(os.path.abspath(EXAMPLE), "local", "hello-cli")
    assert digest.primary_language == "python"
    assert any(e.endswith("cli.py") for e in digest.entry_points)
    assert digest.readme and "text" in digest.readme.lower()


def test_heuristic_analysis_has_run_command():
    digest = repo.build_digest(os.path.abspath(EXAMPLE), "local", "hello-cli")
    analysis = analyzer.analyze_heuristic(digest)
    assert analysis.run_command == "python cli.py"
    assert analysis.integration_strategy == "cli_wrap"
    assert analysis.commands[0].name == "run"


def test_generate_writes_runnable_project(tmp_path):
    digest = repo.build_digest(os.path.abspath(EXAMPLE), "local", "hello-cli")
    analysis = analyzer.analyze_heuristic(digest)
    out = tmp_path / "bot"
    bot_path = generator.generate(analysis, digest, str(out), use_llm=False)
    assert os.path.exists(bot_path)
    for name in ("requirements.txt", ".env.example", "README.md", "Dockerfile"):
        assert (out / name).exists()
    # The generated bot must be syntactically valid Python.
    compile((out / "bot.py").read_text(), "bot.py", "exec")
