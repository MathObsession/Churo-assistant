"""Small smoke test for the ChuroVoice package.

This file used to contain an unrelated ComfyUI script plus a stray PyPI
token line. It is now a simple, self-contained check that the package imports
correctly and exposes the expected version.
"""

from __future__ import annotations


def main() -> int:
    from churovoice import __version__
    from churovoice.assistant import build_parser

    parser = build_parser()
    print(f"churovoice version: {__version__}")
    print(f"cli options: {parser.format_help().splitlines()[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())