"""Turn a RepoDigest into a RepoAnalysis, with or without the LLM."""

import json
from typing import List, Optional

from . import llm
from .config import RUN_TEMPLATE
from .models import BotCommand, RepoAnalysis, RepoDigest

_ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "purpose": {"type": "string"},
        "core_capabilities": {"type": "array", "items": {"type": "string"}},
        "runtime": {"type": "string"},
        "integration_strategy": {
            "type": "string",
            "enum": ["cli_wrap", "reimplement", "api_wrap"],
        },
        "strategy_rationale": {"type": "string"},
        "run_command": {"type": "string"},
        "setup_notes": {"type": "string"},
        "commands": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "usage": {"type": "string"},
                    "parameters": {"type": "array", "items": {"type": "string"}},
                    "maps_to": {"type": "string"},
                },
                "required": ["name", "description", "usage", "parameters", "maps_to"],
            },
        },
    },
    "required": [
        "purpose", "core_capabilities", "runtime", "integration_strategy",
        "strategy_rationale", "run_command", "setup_notes", "commands",
    ],
}

_SYSTEM = """You are a senior engineer designing a Telegram bot that faithfully \
exposes the functionality of a given codebase.

You are given a condensed digest of a repository (file tree, README, manifests, \
and entry-point source). Reproduce the repo's LOGIC, do not just describe it:
- Identify what the project actually does and its genuine, user-facing capabilities.
- Pick an integration strategy:
  * "cli_wrap"    - the repo is a CLI/binary; the bot should invoke it as a subprocess.
  * "reimplement" - the core logic is small and pure; port it directly into the bot.
  * "api_wrap"    - the repo is an importable library; the bot should call its functions.
- Propose 3-8 concrete bot commands that map onto real capabilities of the repo. \
Each command must correspond to something the code can actually do, not an invented feature.
- Give a realistic run_command for the project's entry point.

Refuse to design commands whose purpose is to collect a person's credentials, \
private keys, or other secrets and deliver them to the chat. If that is the repo's \
only purpose, still describe it honestly in `purpose` so the caller's safety check \
can act, but propose no such commands.

Return ONLY structured JSON matching the provided schema."""


def _digest_to_prompt(digest: RepoDigest) -> str:
    lines: List[str] = [
        f"Repository: {digest.name}  ({digest.url})",
        f"Primary language: {digest.primary_language or 'unknown'}",
        f"Language file counts: {json.dumps(digest.languages)}",
        f"Total files: {digest.total_files}"
        + ("  (tree truncated)" if digest.truncated else ""),
        "",
        "FILE TREE (partial):",
        "\n".join(digest.file_tree),
        "",
    ]
    if digest.readme:
        lines += ["README:", digest.readme, ""]
    if digest.entry_points:
        lines += ["ENTRY POINTS: " + ", ".join(digest.entry_points), ""]
    for name, content in digest.manifests.items():
        lines += [f"MANIFEST {name}:", content, ""]
    for path, content in digest.key_files.items():
        lines += [f"FILE {path}:", content, ""]
    return "\n".join(lines)


def _parse_analysis(data: dict) -> RepoAnalysis:
    commands = [
        BotCommand(
            name=str(c["name"]).lstrip("/"),
            description=c["description"],
            usage=c["usage"],
            parameters=list(c.get("parameters", [])),
            maps_to=c.get("maps_to", ""),
        )
        for c in data.get("commands", [])
    ]
    return RepoAnalysis(
        purpose=data["purpose"],
        core_capabilities=list(data.get("core_capabilities", [])),
        runtime=data.get("runtime", "") or "unknown",
        integration_strategy=data.get("integration_strategy", "cli_wrap"),
        strategy_rationale=data.get("strategy_rationale", ""),
        run_command=data.get("run_command") or None,
        setup_notes=data.get("setup_notes", ""),
        commands=commands,
        source="llm",
    )


def analyze_with_llm(digest: RepoDigest, model: Optional[str] = None) -> RepoAnalysis:
    data = llm.analyze_structured(_SYSTEM, _digest_to_prompt(digest), _ANALYSIS_SCHEMA, model)
    return _parse_analysis(data)


# --- Offline heuristic fallback ------------------------------------------

def _default_run_command(digest: RepoDigest) -> Optional[str]:
    lang = digest.primary_language
    if not lang:
        return None
    entry = digest.entry_points[0] if digest.entry_points else None
    template = RUN_TEMPLATE.get(lang)
    if not template:
        return None
    if "{entry}" in template and not entry:
        return None
    return template.format(entry=entry) if entry else template


def analyze_heuristic(digest: RepoDigest) -> RepoAnalysis:
    """A best-effort analysis using only static signals (no LLM)."""
    purpose = f"A {digest.primary_language or 'software'} project named {digest.name}."
    if digest.readme:
        for line in digest.readme.splitlines():
            raw = line.strip()
            # Skip headings, badges, images, links, rules — look for real prose.
            if not raw or raw.startswith(("#", "!", "[", "<", "=", "-", "|", ">", "`")):
                continue
            purpose = raw
            break

    run_command = _default_run_command(digest)
    strategy = "cli_wrap" if run_command else "reimplement"

    commands = [
        BotCommand(
            name="run",
            description=f"Run {digest.name} with the given arguments and return its output.",
            usage="/run <arguments>",
            parameters=["arguments"],
            maps_to="the project's command-line entry point",
        )
    ]
    return RepoAnalysis(
        purpose=purpose,
        core_capabilities=[f"Detected languages: {', '.join(digest.languages) or 'unknown'}"],
        runtime=digest.primary_language or "unknown",
        integration_strategy=strategy,
        strategy_rationale="Heuristic (offline) analysis: wraps the detected entry point.",
        run_command=run_command,
        setup_notes="Generated without the LLM. Review and flesh out the commands by hand, "
        "or re-run with API access for a full logic-aware analysis.",
        commands=commands,
        source="heuristic",
    )


def analyze(digest: RepoDigest, use_llm: bool, model: Optional[str] = None) -> RepoAnalysis:
    if use_llm:
        return analyze_with_llm(digest, model)
    return analyze_heuristic(digest)
