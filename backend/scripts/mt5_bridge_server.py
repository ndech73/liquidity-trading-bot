"""
mt5_bridge_server.py
--------------------
Runs INSIDE Wine, next to MetaTrader 5.
It listens on a port, and the Linux side (mt5linux) calls it
to reach the real MetaTrader5 Python package.
"""

import sys

from rpyc.core import SlaveService
from rpyc.utils.server import ThreadedServer


def main():
    host = "127.0.0.1"  # only this laptop can connect
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18812

    server = ThreadedServer(
        SlaveService,
        hostname=host,
        port=port,
        reuse_addr=True,
        protocol_config={
            "allow_public_attrs": True,
            "allow_all_attrs": True,
            "allow_pickle": True,
            "sync_request_timeout": 300,
        },
    )
    print(f"MT5 bridge listening on {host}:{port}", flush=True)
    server.start()


if __name__ == "__main__":
    main()
