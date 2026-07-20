"""Guardrail: refuse to generate credential/secret exfiltration bots.

A Telegram bot is, by construction, a remote channel that pushes whatever it
produces to a chat. Wrapping a tool that *extracts local credentials or secrets*
in such a bot yields the exfiltration stage of an infostealer, no matter how the
request is framed. This module scans the repo digest and the analysis for that
pattern and blocks generation when it is the clear purpose of the target repo.

It is a heuristic safeguard, not DRM: it aims to stop the obvious abuse case
(browser password/cookie/card stealers, wallet drainers) while leaving ordinary
developer tooling untouched.
"""

from typing import List

from .models import RepoAnalysis, RepoDigest, SafetyVerdict

# Things whose *theft* is the point of an infostealer.
_SECRET_TERMS = [
    "password", "passwords", "cookie", "cookies", "credit card", "creditcard",
    "credit-card", "cvv", "keychain", "login data", "saved login", "autofill",
    "browser data", "browsing data", "master password", "seed phrase",
    "mnemonic", "private key", "wallet.dat", "session token", "auth token",
    "credential", "credentials", "keylogger", "keystroke",
]

# Verbs that turn "handling a secret" into "taking a secret".
_TAKE_TERMS = [
    "steal", "stealer", "exfiltrate", "exfil", "harvest", "dump", "decrypt",
    "extract", "grab", "scrape", "siphon", "recover password", "crack",
]

# Strong nouns that co-locate with the classic browser/credential stealer.
_STRONG_TARGETS = ["browser", "chrome", "firefox", "edge", "chromium", "wallet", "vault"]


def _corpus(digest: RepoDigest, analysis: RepoAnalysis) -> str:
    parts: List[str] = [digest.name, digest.url, analysis.purpose,
                        analysis.strategy_rationale, analysis.setup_notes]
    parts.extend(analysis.core_capabilities)
    parts.extend(c.description + " " + c.maps_to for c in analysis.commands)
    if digest.readme:
        parts.append(digest.readme[:8000])
    parts.extend(digest.file_tree)
    for content in list(digest.key_files.values())[:6]:
        parts.append(content[:4000])
    return "\n".join(p for p in parts if p).lower()


def _hits(corpus: str, terms: List[str]) -> List[str]:
    return sorted({t for t in terms if t in corpus})


def assess(digest: RepoDigest, analysis: RepoAnalysis) -> SafetyVerdict:
    corpus = _corpus(digest, analysis)
    secret_hits = _hits(corpus, _SECRET_TERMS)
    take_hits = _hits(corpus, _TAKE_TERMS)
    strong_hits = _hits(corpus, _STRONG_TARGETS)

    matched = secret_hits + take_hits + strong_hits

    # Clear infostealer signature: a secret target + an extraction verb, and
    # (for the strongest case) a browser/wallet noun. Wrapping this in a bot is
    # remote credential exfiltration.
    if secret_hits and take_hits:
        reason = (
            "The target repository's purpose is extracting or decrypting secrets "
            f"({', '.join(secret_hits[:6])}) via operations like "
            f"{', '.join(take_hits[:4])}. Wrapping that in a Telegram bot builds a "
            "remote credential-exfiltration channel — the exfiltration stage of an "
            "infostealer — so generation is blocked."
        )
        return SafetyVerdict(allowed=False, severity="block", reason=reason, matched=matched)

    # Softer signal: handles secrets but no clear extraction verb (e.g. a password
    # manager, an auth library). Allowed, but the operator is warned.
    if len(secret_hits) >= 2 or (secret_hits and strong_hits):
        reason = (
            "This repo handles sensitive material "
            f"({', '.join(secret_hits[:6])}). Generation is allowed, but do not add "
            "commands that transmit users' secrets to the chat, and only deploy the "
            "bot on systems and accounts you are authorized to operate."
        )
        return SafetyVerdict(allowed=True, severity="warn", reason=reason, matched=matched)

    return SafetyVerdict(allowed=True, severity="ok", reason="No credential-exfiltration signature detected.", matched=matched)
