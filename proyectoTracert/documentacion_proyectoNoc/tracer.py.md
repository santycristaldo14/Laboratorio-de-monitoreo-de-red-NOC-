# tracer.py

**Núcleo de descubrimiento de red.**

## HopResult

Dataclass que modela un salto de red:

| campo         | tipo            | descripción                              |
|---------------|-----------------|------------------------------------------|
| `ttl`         | `int`           | TTL del paquete                          |
| `ip`          | `str` / `None`  | IP del hop (None si timeout)             |
| `hostname`    | `str` / `None`  | DNS reverso                              |
| `rtt_ms`      | `float` / `None`| Round-trip time en ms                    |
| `mac`         | `str` / `None`  | Dirección MAC                            |
| `vendor`      | `str` / `None`  | Fabricante (OUI lookup)                  |
| `mac_scope`   | `"local"`, `"gateway"`, `"unavailable"` | Origen de la MAC |
| `is_destination` | `bool`        | ¿Es el destino final?                    |
| `timed_out`   | `bool`          | No hubo respuesta para este TTL          |

## Funciones principales

### `run_traceroute_stream(target, max_hops=30)`
Generador que itera TTLs 1..30. Por cada uno:
1. Envía un paquete ICMP con ese TTL usando `sr1` de Scapy.
2. Mide tiempo de ida/vuelta.
3. Resuelve hostname por DNS reverso (`_resolve_hostname`).
4. Resuelve MAC según la ubicación del hop:
   - **Misma subred local** → ARP directo (`_arp_lookup`)
   - **Fuera de LAN** → usa la MAC del gateway (`_get_gateway_mac`)
5. Yield del `HopResult`.

### `run_traceroute(target, max_hops=30)`
Wrapper síncrono: llama al generador y devuelve lista completa.

## Funciones auxiliares

| función | qué hace |
|---------|----------|
| `_resolve_hostname(ip)` | `socket.gethostbyaddr` → hostname o `None` |
| `_get_local_network()` | Determina subred local desde tabla de rutas de Scapy |
| `_arp_lookup(ip)` | ARP request + lookup de vendor con `manuf` |
| `_get_gateway_mac()` | ARP a la IP del gateway por defecto |

## Constantes

```python
MAX_HOPS   = 30      # TTL máximo
TIMEOUT    = 2       # timeout ICMP (s)
ARP_TIMEOUT = 1      # timeout ARP (s)
```

➡️ [[main.py]] · [[Arquitectura]]
