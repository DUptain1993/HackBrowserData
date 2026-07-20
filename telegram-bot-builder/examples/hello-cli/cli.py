#!/usr/bin/env python3
"""A tiny text-stats CLI used as a sample target for telegram-bot-builder."""

import argparse


def stats(text: str) -> str:
    words = len(text.split())
    chars = len(text)
    return f"words={words} chars={chars}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Text stats.")
    parser.add_argument("text", help="text to analyze")
    parser.add_argument("--upper", action="store_true", help="also print upper-cased text")
    args = parser.parse_args()
    print(stats(args.text))
    if args.upper:
        print(args.text.upper())


if __name__ == "__main__":
    main()
