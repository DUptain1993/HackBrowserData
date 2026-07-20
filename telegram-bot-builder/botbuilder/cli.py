"""Command-line interface: `botbuilder build|analyze <repo>`."""

import argparse
import json
import shutil
import sys
import tempfile

from . import analyzer, generator, llm, repo, safety
from .config import MODEL


def _resolve_use_llm(requested: str) -> bool:
    """requested is 'auto' | 'on' | 'off'. Returns whether to use the LLM."""
    if requested == "off":
        return False
    usable, reason = llm.availability()
    if requested == "on":
        if not usable:
            print(f"error: --llm requested but unavailable: {reason}", file=sys.stderr)
            sys.exit(2)
        return True
    # auto
    if not usable:
        print(f"note: running in offline heuristic mode ({reason}).", file=sys.stderr)
    return usable


def _load_digest(source: str):
    resolved, is_local = repo.normalize_source(source)
    name = repo.repo_name(source)
    if is_local:
        return repo.build_digest(resolved, resolved, name), None
    tmp = tempfile.mkdtemp(prefix="botbuilder-")
    try:
        repo.clone_repo(resolved, tmp + "/repo")
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return repo.build_digest(tmp + "/repo", resolved, name), tmp


def _print_analysis(analysis) -> None:
    print(f"\nPurpose: {analysis.purpose}")
    print(f"Runtime: {analysis.runtime}   Strategy: {analysis.integration_strategy}")
    if analysis.run_command:
        print(f"Run command: {analysis.run_command}")
    print("Commands:")
    for c in analysis.commands:
        print(f"  {c.usage:<32} {c.description}")


def cmd_analyze(args: argparse.Namespace) -> int:
    use_llm = _resolve_use_llm(args.llm)
    digest, tmp = _load_digest(args.source)
    try:
        analysis = analyzer.analyze(digest, use_llm, args.model)
        verdict = safety.assess(digest, analysis)
        if args.json:
            print(json.dumps({
                "analysis": analysis.to_dict(),
                "safety": {"allowed": verdict.allowed, "severity": verdict.severity,
                           "reason": verdict.reason},
            }, indent=2))
        else:
            _print_analysis(analysis)
            print(f"\nSafety: [{verdict.severity}] {verdict.reason}")
        return 0
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def cmd_build(args: argparse.Namespace) -> int:
    use_llm = _resolve_use_llm(args.llm)
    digest, tmp = _load_digest(args.source)
    try:
        print(f"Analyzing {digest.name} ({'LLM' if use_llm else 'heuristic'}) ...")
        analysis = analyzer.analyze(digest, use_llm, args.model)
        _print_analysis(analysis)

        verdict = safety.assess(digest, analysis)
        print(f"\nSafety: [{verdict.severity}] {verdict.reason}")
        if not verdict.allowed:
            print("\nRefusing to generate a bot for this repository.", file=sys.stderr)
            return 3
        if verdict.severity == "warn" and not args.yes:
            reply = input("\nProceed anyway? [y/N] ").strip().lower()
            if reply not in ("y", "yes"):
                print("Aborted.")
                return 1

        out_dir = args.out or f"./{digest.name}-telegram-bot"
        print(f"\nGenerating bot into {out_dir} ...")
        bot_path = generator.generate(analysis, digest, out_dir, use_llm, args.model)
        print(f"Wrote {bot_path} and supporting files.")
        print(f"\nNext:\n  cd {out_dir}\n  cp .env.example .env   # set BOT_TOKEN\n"
              "  pip install -r requirements.txt\n  python bot.py")
        return 0
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="botbuilder",
        description="Analyze a GitHub repo and build a Telegram bot from its logic.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("source", help="GitHub URL, owner/repo, or local path")
    common.add_argument("--llm", choices=["auto", "on", "off"], default="auto",
                        help="use the Claude API (default: auto-detect)")
    common.add_argument("--model", default=MODEL, help=f"model id (default: {MODEL})")

    p_analyze = sub.add_parser("analyze", parents=[common], help="print analysis only")
    p_analyze.add_argument("--json", action="store_true", help="emit JSON")
    p_analyze.set_defaults(func=cmd_analyze)

    p_build = sub.add_parser("build", parents=[common], help="analyze and generate a bot")
    p_build.add_argument("--out", help="output directory")
    p_build.add_argument("--yes", action="store_true", help="skip confirmation prompts")
    p_build.set_defaults(func=cmd_build)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
