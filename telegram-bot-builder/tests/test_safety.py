"""The guardrail must block credential-stealer repos and pass benign tooling."""

from botbuilder.models import BotCommand, RepoAnalysis, RepoDigest
from botbuilder.safety import assess


def _digest(name, readme, tree=None):
    return RepoDigest(
        name=name, url=f"https://github.com/x/{name}", root="/tmp",
        languages={"go": 3}, primary_language="go", file_tree=tree or [],
        manifests={}, readme=readme, entry_points=[], key_files={},
        total_files=3, truncated=False,
    )


def _analysis(purpose, caps, commands=()):
    return RepoAnalysis(
        purpose=purpose, core_capabilities=list(caps), runtime="go",
        integration_strategy="cli_wrap", strategy_rationale="", run_command="run",
        setup_notes="", commands=list(commands), source="llm",
    )


def test_blocks_browser_credential_stealer():
    digest = _digest(
        "hackbrowserdata",
        "Decrypt and export browser passwords, cookies, and credit cards from Chrome.",
        tree=["browser/chromium.go", "crypto/decrypt.go"],
    )
    analysis = _analysis(
        "Extract and decrypt saved browser passwords, cookies and credit cards.",
        ["decrypt browser passwords", "dump cookies"],
    )
    verdict = assess(digest, analysis)
    assert verdict.allowed is False
    assert verdict.severity == "block"


def test_blocks_wallet_stealer():
    digest = _digest("drainer", "Recover the seed phrase and private key from a wallet.")
    analysis = _analysis("Extract wallet seed phrase and private key.",
                         ["steal private key"])
    verdict = assess(digest, analysis)
    assert verdict.allowed is False


def test_allows_benign_cli():
    digest = _digest("hello-cli", "A tiny text utility: word and character counts.")
    analysis = _analysis("Report word and character counts for input text.",
                         ["count words", "uppercase text"],
                         [BotCommand("stats", "count words", "/stats <text>")])
    verdict = assess(digest, analysis)
    assert verdict.allowed is True
    assert verdict.severity == "ok"


def test_warns_on_password_manager():
    digest = _digest("vaultkeeper", "A personal password manager and secret vault.")
    analysis = _analysis("Store and organize passwords in an encrypted vault.",
                         ["save password", "encrypt vault"])
    verdict = assess(digest, analysis)
    assert verdict.allowed is True
    assert verdict.severity == "warn"
