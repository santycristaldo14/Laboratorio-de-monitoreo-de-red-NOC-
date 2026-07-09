# test_client.py

**Cliente CLI** para probar el WebSocket sin frontend.

## Uso

```bash
# Si el servidor corre en localhost:8000
python test_client.py 8.8.8.8
python test_client.py google.com
```

## Comportamiento

- Conecta a `ws://localhost:8000/ws/trace?target=<target>`
- Procesa los eventos en tiempo real:
  - **start** → muestra el target
  - **hop** → imprime TTL, IP, hostname, RTT, MAC, vendor, tag LAN/GW
  - **done** → confirma finalización
  - **error** → muestra el mensaje de error

Ejemplo de salida:
```
 1  192.168.1.1    (router.local)            2.34 ms   MAC[LAN]: aa:bb:cc:dd:ee:ff [Cisco]
 2  10.0.0.1       (gw.isp.net)              5.12 ms   MAC[GW]: 11:22:33:44:55:66 [Juniper]
...
 8  8.8.8.8        (dns.google)             12.45 ms   MAC[GW]: --  <-- DESTINO

[DONE] Trace finalizado.
```

Depende de la librería `websockets` (cliente).

➡️ [[main.py]] · [[Arquitectura]] · [[Referencia API]]
