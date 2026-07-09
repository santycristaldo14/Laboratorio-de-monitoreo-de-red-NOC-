"""
Cliente de prueba para validar el WebSocket de traceroute sin frontend.

Uso:
    venv/bin/python test_client.py 8.8.8.8
    venv/bin/python test_client.py google.com
"""

import asyncio
import json
import sys

import websockets


async def main(target: str, server: str = "ws://localhost:8000"):
    uri = f"{server}/ws/trace?target={target}"
    print(f"Conectando a {uri} ...\n")

    async with websockets.connect(uri) as ws:
        async for raw_msg in ws:
            msg = json.loads(raw_msg)
            event = msg.get("event")

            if event == "start":
                print(f"[START] Trazando ruta hacia {msg['target']}\n")

            elif event == "hop":
                h = msg["data"]
                if h["timed_out"]:
                    print(f"  {h['ttl']:>2}  *  *  *  (sin respuesta)")
                else:
                    ip = h["ip"]
                    host = f" ({h['hostname']})" if h["hostname"] else ""
                    mac = h["mac"] or "N/A"
                    vendor = f" [{h['vendor']}]" if h["vendor"] else ""
                    scope_tag = {
                        "local": "LAN",
                        "gateway": "GW",
                        "unavailable": "--",
                    }.get(h["mac_scope"], "--")
                    dest_tag = "  <-- DESTINO" if h["is_destination"] else ""
                    print(
                        f"  {h['ttl']:>2}  {ip:<15}{host:<30} "
                        f"{h['rtt_ms']:>7.2f} ms   MAC[{scope_tag}]: {mac}{vendor}{dest_tag}"
                    )

            elif event == "done":
                print("\n[DONE] Trace finalizado.")

            elif event == "error":
                print(f"\n[ERROR] {msg['message']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python test_client.py <ip-o-hostname>")
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
