# V0.1.1 — ChuroVoice launcher.
#
# This script is a thin wrapper around the cross-platform ``churovoice``
# package. All real logic lives in ``churovoice/assistant.py`` and the
# platform-specific bits (audio playback, app launching, app discovery) live
# in ``churovoice/platform_utils.py`` so that the assistant runs on macOS,
# Windows, and (with minimal extra effort) Linux without any code changes.
#
# Run it with:
#
#     python main.py            # interactive voice
#     python main.py --voice male
#     python main.py --voice female

from __future__ import annotations

import os
import sys


def main() -> int:
    # Make sure the local package is importable when running this file from
    # the project root (``python main.py``) or from anywhere else.
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)

    from churovoice.assistant import main as assistant_main

    # Strip the program name so ``argparse`` inside ``assistant_main`` sees
    # only the user-supplied flags.
    assistant_main(sys.argv[1:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
