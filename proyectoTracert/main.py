"""
Servidor FastAPI - Fase 1.

Expone:
  - GET  /                         -> healthcheck simple
  - WS   /ws/trace?target=<host>   -> stream de hops en tiempo real

Debe ejecutarse con privilegios root (Scapy necesita raw sockets):
    sudo venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.tracer import run_traceroute_stream

app = FastAPI(title="NetViz - Fase 1")

# CORS abierto para desarrollo local (ajustar en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def healthcheck():
    return {"status": "ok", "service": "netviz-backend", "phase": 1}


@app.websocket("/ws/trace")
async def ws_trace(websocket: WebSocket):
    await websocket.accept()
    target = websocket.query_params.get("target")

    if not target:
        await websocket.send_json({"error": "Falta el parámetro 'target'"})
        await websocket.close()
        return

    await websocket.send_json({"event": "start", "target": target})

    try:
        loop = asyncio.get_event_loop()

        # run_traceroute_stream es un generador SINCRÓNICO (Scapy bloquea),
        # así que lo iteramos en un executor para no congelar el event loop.
        def _blocking_iter():
            return list(run_traceroute_stream(target))

        # Para verdadero streaming hop-a-hop sin esperar el trace completo,
        # corremos cada paso del generador en el executor por separado.
        gen = run_traceroute_stream(target)

        def _next_hop():
            try:
                return next(gen)
            except StopIteration:
                return None

        while True:
            hop = await loop.run_in_executor(None, _next_hop)
            if hop is None:
                break

            await websocket.send_json({"event": "hop", "data": hop.to_dict()})

            if hop.is_destination:
                break

        await websocket.send_json({"event": "done"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"event": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
