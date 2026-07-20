"""Central configuration and static lookup tables for the bot builder."""

import os

# --- Model / LLM settings -------------------------------------------------

# Default model. Override with BOTBUILDER_MODEL. Opus 4.8 is the most capable
# model for the "understand a codebase then reproduce its logic" task.
MODEL = os.environ.get("BOTBUILDER_MODEL", "claude-opus-4-8")

# Non-streaming ceiling that keeps requests under SDK HTTP timeouts.
ANALYSIS_MAX_TOKENS = 16000
# Generation streams, so it can ask for a lot more room.
GENERATION_MAX_TOKENS = 32000

# --- Digest limits --------------------------------------------------------

MAX_FILE_BYTES = 24_000          # per key file read into the digest
MAX_TOTAL_DIGEST_BYTES = 180_000  # rough cap on all key-file content combined
MAX_TREE_ENTRIES = 400           # relative paths listed in the file tree

# Directories that never contain source worth analyzing.
IGNORE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", "dist", "build", "target",
    ".venv", "venv", "env", "__pycache__", ".idea", ".vscode", ".next", "out",
    "bin", "obj", ".gradle", "coverage", ".mypy_cache", ".pytest_cache",
    "site-packages", ".tox", ".cache", "Pods", "DerivedData",
}

# Files that identify a project's toolchain / entry configuration.
MANIFEST_FILES = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "Pipfile", "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
    "build.gradle.kts", "composer.json", "Gemfile", "mix.exs", "CMakeLists.txt",
    "Makefile", "makefile", "pubspec.yaml",
}

# Common single-file entry points, by basename.
ENTRY_POINT_NAMES = {
    "main.py", "__main__.py", "app.py", "cli.py", "manage.py", "run.py",
    "index.js", "main.js", "server.js", "app.js", "cli.js",
    "index.ts", "main.ts", "cli.ts", "server.ts",
    "main.go", "main.rs", "Main.java", "main.c", "main.cpp",
}

# Source extension -> language name (used to guess the primary language).
LANG_BY_EXT = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".go": "go", ".rs": "rust",
    ".java": "java", ".kt": "kotlin", ".rb": "ruby", ".php": "php",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".cs": "csharp", ".swift": "swift", ".scala": "scala", ".dart": "dart",
    ".sh": "shell", ".ex": "elixir", ".exs": "elixir",
}

# How to invoke a project's entry point, keyed by detected language.
RUN_TEMPLATE = {
    "python": "python {entry}",
    "javascript": "node {entry}",
    "typescript": "node {entry}",
    "go": "go run .",
    "rust": "cargo run --",
    "ruby": "ruby {entry}",
    "php": "php {entry}",
    "java": "java {entry}",
    "shell": "bash {entry}",
}
