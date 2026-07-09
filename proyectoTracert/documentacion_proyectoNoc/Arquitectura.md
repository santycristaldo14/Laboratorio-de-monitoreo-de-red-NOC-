# Arquitectura

```
┌──────────────┐   WebSocket    ┌──────────────┐   ICMP/ARP    ┌─────────┐
│  Cliente     │ ───────────────→│  main.py     │ ────────────→│  Red    │
│  (test_client│ ←───────────────│  (FastAPI)   │ ←────────────│         │
│   o frontend)│   JSON stream   │              │              └─────────┘
└──────────────┘                 └──────┬───────┘
                                        │ llama a
                                        ▼
                                 ┌──────────────┐
                                 │  tracer.py   │
                                 │  (core)      │
                                 └──────────────┘
```

## Flujo

1. Cliente conecta a `ws://host:8000/ws/trace?target=<ip|dominio>`
2. `main.py` acepta y delega en `tracer.run_traceroute_stream(target)`
3. El generador produce un `HopResult` por cada TTL (1..30)
4. `main.py` envía cada hop al cliente en cuanto está listo (streaming real)
5. Al llegar al destino o agotar TTLs, envía `{"event": "done"}`

## Eventos WebSocket

| event | significado                        |
| ----- | ---------------------------------- |
| start | Inicio del trace con `target`      |
| hop   | Un salto descubierto               |
| done  | Trace completado                   |
| error | Error (target inválido, red, etc.) |

➡️ [[main.py]] · [[tracer.py]] · [[test_client.py]]
