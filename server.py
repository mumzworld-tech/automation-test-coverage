#!/usr/bin/env python3
"""Serve the report, rebuilding it from automation_web_2.0 @ main on demand.

Nothing is scheduled. When a visitor's page asks for mapping.json, this checks
whether main has moved (at most once a minute, however many people are on the
page) and, if it has, reruns the same extract -> map -> verify chain as
`make generate` before answering. A rebuild takes a couple of seconds; a check
that finds nothing new is one `git fetch`.

automation_web_2.0 is private, so the token lives here, in the server's
environment, and never reaches the browser:

    AUTOMATION_REPO_TOKEN  classic PAT, `repo` scope (the org rejects fine-grained)
    PORT                   default 8080
    DATA_DIR               where the clone lives; default /data, else ./.data

If a fetch or rebuild fails, the last good report is served and the error is
logged -- visitors never see a broken page because GitHub hiccuped.

    AUTOMATION_REPO_TOKEN=... python3 server.py
"""
import base64
import os
import shutil
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
REPO_URL = "https://github.com/mumzworld-tech/automation_web_2.0.git"
CHECK_EVERY = 60          # seconds between `git fetch`es, shared by all visitors
BUILT = ("automated_tests.json", "mapping.json")
# Data only -- never serve the scripts, the TestMO exports' sources or .git.
PUBLIC = {"/", "/index.html", "/mapping.json", "/automated_tests.json",
          "/tenure.json", "/runs.json", "/favicon.ico"}

DATA = Path(os.environ.get("DATA_DIR") or ("/data" if Path("/data").is_dir() else HERE / ".data"))
CLONE = DATA / "automation_web_2.0"
_lock = threading.Lock()
_state = {"checked": 0.0, "built": None}


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, file=sys.stderr, flush=True)


def git(*args):
    # The token goes in a per-command header, so it is never written to
    # .git/config or shown in a remote URL.
    token = os.environ["AUTOMATION_REPO_TOKEN"]
    auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    try:
        return subprocess.run(["git", "-c", f"http.extraHeader=Authorization: Basic {auth}", *args],
                              capture_output=True, text=True, check=True, timeout=120).stdout.strip()
    except subprocess.CalledProcessError as e:
        # Re-raised without the command line: it carries the token.
        raise RuntimeError(f"git {args[0] if args[0] != '-C' else args[2]} failed: {e.stderr.strip()[-300:]}") from None


def main_sha():
    if not (CLONE / "HEAD").exists():
        log("cloning automation_web_2.0 ...")
        CLONE.parent.mkdir(parents=True, exist_ok=True)
        # Bare and full: extract_tests.py only reads origin/main through
        # `git show`, and it needs the history to find Arabic-locale tickets.
        git("clone", "--bare", "--quiet", REPO_URL, str(CLONE))
        git("-C", str(CLONE), "config", "remote.origin.fetch", "+refs/heads/main:refs/remotes/origin/main")
    git("-C", str(CLONE), "fetch", "--quiet", "--prune", "origin")
    return git("-C", str(CLONE), "rev-parse", "origin/main")


def rebuild():
    # Build in a copy of the project, then swap the results in with an atomic
    # rename: visitors keep reading the old files until the new ones are whole
    # and verified, and a failed build leaves them untouched.
    stage = HERE / ".stage"                     # same filesystem as HERE, or the rename fails
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)
    for f in [*HERE.glob("*.py"), *HERE.glob("*.json")]:
        shutil.copy2(f, stage)
    try:
        for step in (["extract_tests.py", str(CLONE)], ["build_mapping.py"], ["verify_mapping.py"]):
            subprocess.run([sys.executable, str(stage / step[0]), *step[1:]], cwd=stage,
                           capture_output=True, text=True, check=True, timeout=120)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"{Path(e.cmd[1]).name} failed: {(e.stderr or e.stdout).strip()[-500:]}") from None
    for f in BUILT:
        os.replace(stage / f, HERE / f)


def refresh():
    """Bring mapping.json up to main, at most once every CHECK_EVERY seconds."""
    # A visitor who arrives mid-refresh gets the current report at once rather
    # than waiting -- the first clone alone takes ~30s.
    if not _lock.acquire(blocking=False):
        return
    try:
        if time.time() - _state["checked"] < CHECK_EVERY:
            return
        _state["checked"] = time.time()
        try:
            sha = main_sha()
            if sha != _state["built"]:
                started = time.time()
                rebuild()
                _state["built"] = sha
                log(f"rebuilt from main @ {sha[:7]} in {time.time() - started:.1f}s")
        except Exception as e:                  # noqa: BLE001 -- any failure: serve what we have
            log(f"refresh failed, serving the last good report: {e}")
    finally:
        _lock.release()


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/healthz":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if path not in PUBLIC:
            self.send_error(404)
            return
        if path == "/mapping.json":
            refresh()
        super().do_GET()

    def end_headers(self):
        # The page appends ?t=... to its data fetches anyway; this also stops a
        # proxy in front of Coolify from caching a stale report.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format, *args):  # noqa: A002 -- the base class's name
        pass                                    # only refreshes are worth logging


def serve():
    if not os.environ.get("AUTOMATION_REPO_TOKEN"):
        sys.exit("AUTOMATION_REPO_TOKEN is not set: a classic PAT (repo scope) that can read "
                 "mumzworld-tech/automation_web_2.0")
    if not shutil.which("git"):
        sys.exit("git is not installed")
    threading.Thread(target=refresh, daemon=True).start()   # warm the clone before the first visitor
    port = int(os.environ.get("PORT", "8080"))
    log(f"serving on :{port}")
    ThreadingHTTPServer(("", port), partial(Handler, directory=str(HERE))).serve_forever()


if __name__ == "__main__":
    serve()
