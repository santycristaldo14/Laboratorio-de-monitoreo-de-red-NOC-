# main.py

**Servidor FastAPI** — punto de entrada.

## Endpoints

### `GET /`
Healthcheck simple:
```json
{"status": "ok", "service": "netviz-backend", "phase": 1}
```

### `WS /ws/trace?target=<host>`
WebSocket que streamea los hops del traceroute.

## Detalles clave

- **CORS abierto** (`allow_origins=["*"]`) — solo para desarrollo.
- El generador `run_traceroute_stream` es **síncrono** (Scapy bloquea). Para no congelar el event loop de asyncio, se itera dentro de un `run_in_executor` llamando a `next(gen)` paso a paso.
- Así se logra **streaming real**: el cliente recibe cada hop ni bien está listo, sin esperar el trace completo.
- Maneja `WebSocketDisconnect` limpiamente.

```python
# Ejemplo: iterar generador síncrono en executor
gen = run_traceroute_stream(target)
while True:
    hop = await loop.run_in_executor(None, next, gen)
    if hop is None:
        break
    await websocket.send_json({"event": "hop", "data": hop.to_dict()})
```

## Ejecución

Requiere **root** por los raw sockets de Scapy:
```bash
sudo uvicorn app.main:app --host 0.0.0.0 --port 8000
```

➡️ [[Arquitectura]] · [[tracer.py]]
