"""Live test harness for the *minimal* Emby API wrapper.

Usage::

    export EMBY_URL="http://your-emby:8096"
    export EMBY_API_KEY="xxxxxxxxxxxxxxxx"

    python -m devtools.emby_harness --search "The Matrix"

The script is **optional** – it only runs if the required environment
variables are set.  It can be executed on its own without a running Home
Assistant instance, which helps rapid development of the Emby helper classes.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from urllib.parse import urlparse


async def _amain() -> None:  # noqa: ANN201
    # Local import so that developers can run the harness against an *editable*
    # checkout without installing the integration as a package.
    from custom_components.emby.api import EmbyAPI  # local import for editable repo

    emby_url = os.getenv("EMBY_URL")
    api_key = os.getenv("EMBY_API_KEY")

    if not emby_url or not api_key:
        print("EMBY_URL and/or EMBY_API_KEY environment variables not set – nothing to do.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Quick Emby API helper harness")
    parser.add_argument("--search", help="Search term to look for in the library", default=None)
    args = parser.parse_args()

    parsed = urlparse(emby_url)
    host = parsed.hostname or "localhost"
    port = parsed.port  # can be None
    ssl = parsed.scheme == "https"

    api = EmbyAPI(None, host, api_key, ssl=ssl, port=port)

    sessions = await api.get_sessions(force_refresh=True)
    print(f"Active sessions: {len(sessions)}")
    for sess in sessions:
        device = sess.get("DeviceName") or sess.get("Client")
        print(f" • {sess.get('Id')}  {device}  State={sess.get('PlayState', {}).get('State')}")

    if args.search:
        results = await api.search(search_term=args.search, limit=5)
        print("Search results:")
        for itm in results:
            print(f" • {itm.get('Id')}  {itm.get('Name')}  ({itm.get('Type')})")


def main() -> None:  # noqa: ANN001 – entrypoint
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
