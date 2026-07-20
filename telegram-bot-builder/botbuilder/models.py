r"""Plain dataclasses passed between the pipeline stages.

repo -> RepoDigest -> analyzer -> RepoAnalysis -> safety -> SafetyVerdict
                                              \-> generator -> files on disk
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class RepoDigest:
    """A condensed, token-bounded view of a repository."""

    name: str
    url: str
    root: str
    languages: Dict[str, int]              # language name -> source file count
    primary_language: Optional[str]
    file_tree: List[str]                   # relative paths (truncated)
    manifests: Dict[str, str]              # basename -> content (truncated)
    readme: Optional[str]
    entry_points: List[str]                # relative paths
    key_files: Dict[str, str]              # relative path -> content (truncated)
    total_files: int
    truncated: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BotCommand:
    name: str                              # e.g. "convert" (no leading slash)
    description: str
    usage: str                             # e.g. "/convert <text>"
    parameters: List[str] = field(default_factory=list)
    maps_to: str = ""                      # which repo capability it exposes

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RepoAnalysis:
    purpose: str
    core_capabilities: List[str]
    runtime: str                           # "python" | "node" | "go" | ...
    integration_strategy: str              # "cli_wrap" | "reimplement" | "api_wrap"
    strategy_rationale: str
    run_command: Optional[str]
    setup_notes: str
    commands: List[BotCommand]
    source: str = "heuristic"              # "llm" | "heuristic"

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


@dataclass
class SafetyVerdict:
    allowed: bool
    severity: str                          # "ok" | "warn" | "block"
    reason: str
    matched: List[str] = field(default_factory=list)
