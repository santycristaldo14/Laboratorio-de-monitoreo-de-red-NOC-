# NOC Monitoring Stack

Stack de monitoreo de tráfico de red basado en NetFlow, pensado para
laboratorio: un router Mikrotik exporta NetFlow, y un pipeline en Docker
lo traduce y visualiza en un dashboard web.

Proyecto de portfolio orientado a NOC / seguridad de redes, con foco en
entender a fondo cómo funciona la captura y análisis de tráfico antes de
migrar equivalentes a servicios cloud (AWS).

## Arquitectura

```
Mikrotik --NetFlow v9 UDP:2055--> netflow2ng --ZMQ TCP:5556--> ntopng (web UI :3000)
```

- **netflow2ng**: recibe el NetFlow crudo del router y lo traduce a un
  formato que ntopng puede consumir vía ZMQ. Es necesario porque **ntopng
  community edition no puede recibir NetFlow crudo directamente** (esa
  capacidad requiere nProbe, que es de pago). netflow2ng es la alternativa
  libre y gratuita.
- **redis**: almacena el estado interno de ntopng (contadores, cache de hosts).
- **ntopng**: dashboard web de visualización de tráfico (hosts, flows,
  protocolos vía nDPI).

Créditos / imágenes usadas:
- [synfinatic/netflow2ng](https://github.com/synfinatic/netflow2ng)
- [ntop/ntopng](https://github.com/ntop/ntopng)
- [docker-library/redis](https://github.com/docker-library/redis)

## Prerequisitos

- Un router Mikrotik (RouterOS) con capacidad de exportar NetFlow v9
  (probado sobre un RB2011).
- Docker y Docker Compose instalados en la máquina donde vas a correr el
  stack.
- Conectividad de red entre el Mikrotik y esa máquina.

> Recomendado para pruebas: aislar el router de cualquier red de
> producción hasta validar el pipeline completo.

## Configuración del Mikrotik

Reemplazá `192.168.88.10` por la IP de la máquina donde corre el stack, y
`192.168.88.1` por la IP del propio router:

```
/ip traffic-flow
set enabled=yes interfaces=all

/ip traffic-flow target
add dst-address=192.168.88.10 port=2055 version=9 src-address=192.168.88.1
```

Verificar que el target haya quedado habilitado (por default se crea
deshabilitado):

```
/ip traffic-flow target print detail
```

## Instalación

1. Cloná el repo y entrá a la carpeta del stack:
   ```bash
   git clone <url-del-repo>
   cd ntopng-stack
   ```

2. Si tu red del Mikrotik no es `192.168.88.0/24`, ajustá el valor de
   `--local-networks` en `docker-compose.yml`.

3. Levantá el stack:
   ```bash
   docker compose up -d
   ```

4. Entrá al dashboard desde el navegador:
   ```
   http://localhost:3000
   ```

## Verificación

Antes de levantar Docker, podés confirmar que el NetFlow del router está
llegando:

```bash
sudo tcpdump -i <tu_interfaz> udp port 2055
```

Para chequear que los puertos del stack están escuchando (apuntá a la
máquina donde corre Docker, **no** al router — el router solo envía
NetFlow, no escucha nada):

```bash
nmap -sU -p 2055 localhost
nmap -p 3000,5556 localhost
```

## Notas técnicas

- Los tres servicios usan `network_mode: host`. Es obligatorio: con NAT
  de Docker (modo bridge default), el puerto de origen de los paquetes
  NetFlow entrantes cambia y netflow2ng no los puede procesar
  correctamente.
- Como consecuencia, `EXPOSE`/`ports:` no cumplen ninguna función acá —
  con `host` networking los contenedores comparten la pila de red del
  host directamente, sin mapeo de puertos.

## Roadmap

- Port mirroring en el switch chip del Mikrotik + Suricata como IDS, para
  cubrir tráfico entre dispositivos del mismo segmento L2 que no pasa por
  el router (y por lo tanto no es capturado por NetFlow).
- Versión equivalente en AWS (NetFlow → VPC Flow Logs / Traffic Mirroring).
- Integración con el proyecto hermano "Packet Visualizer" (FastAPI +
  Scapy) para diagramar hops de red.
