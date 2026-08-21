"""Keep the public Streamlit Community Cloud demo reachable.

Community Cloud puts an app to sleep after roughly 12 hours without a viewer,
and waking it again needs the owner's session (an anonymous POST to
/api/v2/app/resume returns 403). So this script prevents the sleep instead of
recovering from it: it opens a real viewer websocket session on a schedule.

Two things are checked, and either one failing exits non-zero so the scheduled
run goes red rather than failing silently:

  1. The app container answers /~/+/_stcore/health with "ok". Note the /~/+/
     prefix -- Community Cloud serves a wrapper SPA at the domain root, and
     that wrapper answers /_stcore/health with its own HTML, so probing the
     bare path reports success even when the app is asleep.
  2. A websocket to /~/+/_stcore/stream opens. That is what a browser tab does
     and what actually counts as a viewer session.
"""

from __future__ import annotations

import asyncio
import http.cookiejar
import os
import sys
import urllib.request

import websockets

APP_HOST = os.environ.get("APP_HOST", "wefinance-copilot.streamlit.app")
HEALTH_URL = f"https://{APP_HOST}/~/+/_stcore/health"
STREAM_URL = f"wss://{APP_HOST}/~/+/_stcore/stream"
TIMEOUT = int(os.environ.get("TIMEOUT_SECONDS", "45"))


def open_session() -> str:
    """Follow the cookie-setting redirect a browser follows, return the Cookie header."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.open(f"https://{APP_HOST}/", timeout=TIMEOUT).read()
    return "; ".join(f"{c.name}={c.value}" for c in jar)


def check_health(cookie: str) -> str:
    request = urllib.request.Request(HEALTH_URL, headers={"Cookie": cookie})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", "replace").strip()


async def hold_viewer_session(cookie: str) -> None:
    async with websockets.connect(
        STREAM_URL,
        additional_headers={"Cookie": cookie},
        origin=f"https://{APP_HOST}",
        open_timeout=TIMEOUT,
    ):
        # Holding the socket briefly is what registers a viewer session; the
        # app does not push a frame until the client sends a BackMsg, so we
        # deliberately do not wait on recv().
        await asyncio.sleep(5)


def main() -> int:
    cookie = open_session()

    body = check_health(cookie)
    if body != "ok":
        print(f"::error::app health check returned {body[:120]!r}, expected 'ok'")
        return 1
    print("health: ok")

    try:
        asyncio.run(hold_viewer_session(cookie))
    except Exception as exc:  # any failure to connect is worth reporting
        print(f"::error::could not open a viewer websocket: {type(exc).__name__}: {exc}")
        return 1
    print("viewer session: held 5s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
