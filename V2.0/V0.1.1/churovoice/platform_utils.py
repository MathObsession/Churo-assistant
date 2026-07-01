"""Cross-platform helpers for ChuroVoice.

This module abstracts away the parts of the assistant that are inherently
operating-system specific so the rest of the codebase can stay clean:

*   TTS playback (``afplay`` on macOS, PowerShell's ``Media.SoundPlayer`` on
    Windows, ``mpg123``/``ffplay``/``paplay``/``aplay`` fallbacks on Linux).
*   App / URL launching (``open`` on macOS, ``start`` on Windows, ``xdg-open``
    on Linux).
*   Application discovery (``mdfind`` on macOS, the Windows registry / Start
    Menu shortcuts on Windows, ``.desktop`` files / ``which`` on Linux).

The helpers all return ``False`` (rather than raising) when an OS-specific
tool is missing so the assistant can degrade gracefully on any platform.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from functools import lru_cache
from typing import Iterable


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def current_platform() -> str:
    """Return ``"darwin"``, ``"windows"``, ``"linux"`` or ``"other"``."""
    system = platform.system().lower()
    if system.startswith("darwin") or system == "macos":
        return "darwin"
    if system.startswith("windows"):
        return "windows"
    if system.startswith("linux"):
        return "linux"
    return "other"


def is_macos() -> bool:
    return current_platform() == "darwin"


def is_windows() -> bool:
    return current_platform() == "windows"


def is_linux() -> bool:
    return current_platform() == "linux"


# ---------------------------------------------------------------------------
# TTS playback
# ---------------------------------------------------------------------------

# Candidate audio players tried in order on each platform. The first one that
# exists on ``PATH`` wins. ``None`` means "use the platform's built-in".
_AUDIO_PLAYERS_LINUX: tuple[str, ...] = ("mpg123", "ffplay", "paplay", "aplay")


def _resolve_linux_player() -> str | None:
    for candidate in _AUDIO_PLAYERS_LINUX:
        path = shutil.which(candidate)
        if path:
            return path
    return None


def play_audio(path: str) -> bool:
    """Play an audio file using whatever the host platform offers.

    Returns ``True`` if a playback command was launched, ``False`` otherwise.
    The caller is responsible for the file's lifetime (we never delete it
    here, so tests can inspect the output).
    """

    if not path or not os.path.exists(path):
        return False

    plat = current_platform()

    if is_macos():
        # ``afplay`` ships with macOS - always available.
        return subprocess.run(["afplay", path], check=False).returncode == 0

    if is_windows():
        # Use PowerShell's SoundPlayer so we don't need any third-party CLI.
        # ``start``/``wmp`` would block waiting for a player window.
        ps_command = (
            "(New-Object Media.SoundPlayer '" + path.replace("'", "''") + "')."
            "PlaySync()"
        )
        return subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            check=False,
        ).returncode == 0

    # Linux / other Unix-like
    player = _resolve_linux_player()
    if player is None:
        return False

    args = [player]
    if player.endswith("ffplay"):
        args += ["-nodisp", "-autoexit", "-loglevel", "error"]
    args.append(path)
    return subprocess.run(args, check=False).returncode == 0


# ---------------------------------------------------------------------------
# App / URL launching
# ---------------------------------------------------------------------------

def open_url(url: str) -> bool:
    """Open *url* in the platform's default handler. Returns ``False`` on
    failure so callers can fall back."""

    if not url:
        return False

    plat = current_platform()

    try:
        if is_macos():
            subprocess.Popen(["open", url])
        elif is_windows():
            # ``start`` is a shell builtin; call it through ``cmd``.
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
        else:
            opener = shutil.which("xdg-open")
            if opener is None:
                return False
            subprocess.Popen([opener, url])
        return True
    except OSError:
        return False


def open_path(path: str) -> bool:
    """Open a local file or directory in the platform's default handler."""

    if not path:
        return False

    plat = current_platform()

    try:
        if is_macos():
            subprocess.Popen(["open", path])
        elif is_windows():
            subprocess.Popen(["cmd", "/c", "start", "", path], shell=False)
        else:
            opener = shutil.which("xdg-open")
            if opener is None:
                return False
            subprocess.Popen([opener, path])
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Application discovery
# ---------------------------------------------------------------------------

def _find_macos_apps(query: str) -> list[str]:
    if shutil.which("mdfind") is None:
        return []
    try:
        result = subprocess.run(
            ["mdfind", 'kMDItemKind == "Application"'],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    return [line for line in result.stdout.splitlines() if query.lower() in line.lower()]


def _find_windows_apps(query: str) -> list[str]:
    """Search the Windows Start Menu for matching shortcuts.

    The Start Menu contains ``.lnk`` files whose names are the human-readable
    app names. This is a reasonable lightweight approximation of macOS's
    ``mdfind`` and works without PowerShell COM calls.
    """

    matches: list[str] = []

    start_dirs = [
        os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
    ]

    needle = query.lower().strip()
    if not needle:
        return matches

    for start_dir in start_dirs:
        if not start_dir or not os.path.isdir(start_dir):
            continue
        for root, _dirs, files in os.walk(start_dir):
            for filename in files:
                if not filename.lower().endswith(".lnk"):
                    continue
                base = os.path.splitext(filename)[0]
                if needle in base.lower():
                    matches.append(os.path.join(root, filename))
                    if len(matches) >= 5:
                        return matches

    return matches


def _find_linux_apps(query: str) -> list[str]:
    """Look for ``.desktop`` files whose ``Name=`` matches the query."""

    matches: list[str] = []
    needle = query.lower().strip()
    if not needle:
        return matches

    search_dirs = [
        "/usr/share/applications",
        "/usr/local/share/applications",
        os.path.expanduser("~/.local/share/applications"),
        os.path.expanduser("~/.gnome/apps"),
    ]

    for app_dir in search_dirs:
        if not os.path.isdir(app_dir):
            continue
        for entry in os.listdir(app_dir):
            if not entry.lower().endswith(".desktop"):
                continue
            path = os.path.join(app_dir, entry)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    for line in fp:
                        if line.lower().startswith("name=") and needle in line.lower():
                            matches.append(path)
                            break
            except OSError:
                continue
            if len(matches) >= 5:
                return matches

    return matches


def find_applications(query: str) -> list[str]:
    """Return a list of application paths matching *query* on the host OS."""

    query = (query or "").strip()
    if not query:
        return []

    if is_macos():
        return _find_macos_apps(query)
    if is_windows():
        return _find_windows_apps(query)
    if is_linux():
        return _find_linux_apps(query)
    return []


# ---------------------------------------------------------------------------
# Image preview
# ---------------------------------------------------------------------------

def preview_image_in_terminal(path: str, width: int = 60) -> bool:
    """Render *path* in the terminal if possible.

    macOS and Linux use ``chafa`` when present; on Windows we fall back to
    printing a ``Saved to <path>`` message because most Windows terminals
    don't speak the iTerm/Kitty image protocols.
    """

    if not path or not os.path.exists(path):
        return False

    chafa = shutil.which("chafa")
    if chafa and not is_windows():
        return subprocess.run(
            [chafa, path, "--symbols", "block", f"--size={width}"],
            check=False,
        ).returncode == 0

    if is_windows():
        print(f"Generated image saved to {path}")
        return True

    return False


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

def python_executable() -> str:
    """Return ``sys.executable`` (handy for platform-agnostic subprocess
    invocations)."""
    return sys.executable


def user_friendly_os_name() -> str:
    return {
        "darwin": "macOS",
        "windows": "Windows",
        "linux": "Linux",
        "other": platform.system() or "Unknown",
    }.get(current_platform(), platform.system() or "Unknown")
