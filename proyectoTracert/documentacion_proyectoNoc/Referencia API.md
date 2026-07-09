# Referencia API

## `GET /`

```json
{"status": "ok", "service": "netviz-backend", "phase": 1}
```

## `WS /ws/trace?target=<host>`

### Eventos

#### `start`
```json
{"event": "start", "target": "8.8.8.8"}
```

#### `hop`
```json
{
  "event": "hop",
  "data": {
    "ttl": 1,
    "ip": "192.168.1.1",
    "hostname": "router.local",
    "rtt_ms": 2.34,
    "mac": "aa:bb:cc:dd:ee:ff",
    "vendor": "Cisco",
    "mac_scope": "local",
    "is_destination": false,
    "timed_out": false
  }
}
```

#### `done`
```json
{"event": "done"}
```

#### `error`
```json
{"event": "error", "message": "Could not resolve host: inexistente"}
```

## Dependencias (`requirements.txt`)

| librería | uso |
|----------|-----|
| fastapi | Framework web |
| uvicorn | Servidor ASGI |
| scapy | Paquetes ICMP y ARP (raw sockets) |
| manuf | Lookup de fabricante por OUI |
| websockets | Cliente WebSocket (test) |

## Ejecución

```bash
sudo venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

➡️ [[main.py]] · [[tracer.py]] · [[test_client.py]]
