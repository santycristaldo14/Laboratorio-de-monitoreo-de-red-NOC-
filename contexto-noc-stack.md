# Contexto: NOC Monitoring Stack (Mikrotik RB2011 + Docker)

## Objetivo del proyecto
Armar un stack de monitoreo de tráfico de red en una notebook con Arch Linux,
usando un Mikrotik RB2011 aislado como fuente de tráfico (parte de un portfolio
de homelab orientado a NOC / cloud security).

## Arquitectura
```
RB2011 --NetFlow v9 UDP:2055--> netflow2ng --ZMQ TCP:5556--> ntopng (web UI :3000)
```

- **netflow2ng**: recibe el NetFlow crudo del Mikrotik y lo traduce a un
  formato que ntopng puede consumir vía ZMQ. Necesario porque **ntopng
  community edition no puede recibir NetFlow crudo directamente** (esa
  capacidad requiere nProbe, que es de pago; netflow2ng es la alternativa
  libre y gratuita).
- **redis**: estado interno de ntopng (contadores, cache de hosts).
- **ntopng**: dashboard web de visualización de tráfico.

Repos fuente de las imágenes usadas:
- https://github.com/synfinatic/netflow2ng
- https://github.com/ntop/ntopng
- https://github.com/docker-library/redis

## Entorno
- **Notebook**: Arch Linux, Docker + docker-compose instalados y funcionando
  (usuario agregado al grupo `docker`).
- **Router**: Mikrotik RB2011 (tiene switch chip), usado **aislado** de la
  red de trabajo para pruebas sin riesgo.
- **Red de laboratorio**: `192.168.88.0/24` (default del Mikrotik).
- **IP fija de la notebook** en esa red: `192.168.88.10` (asignada vía
  NetworkManager/`nmcli` sobre la interfaz cableada conectada al RB2011).
- Se sumó una segunda PC conectada al RB2011 para generar tráfico de
  "otro dispositivo" y validar que el NetFlow lo captura.

## Configuración aplicada en el Mikrotik (RouterOS)
```
/ip traffic-flow
set enabled=yes interfaces=all

/ip traffic-flow target
add dst-address=192.168.88.10 port=2055 version=9 src-address=192.168.88.1
```

Notas importantes:
- El parámetro correcto es `dst-address`, no `address`.
- `src-address` va **dentro del `target add`**, no en el `set` general
  (poner-lo en `set` tira error).
- Los targets nuevos quedan **disabled** por default; hay que habilitarlos:
  ```
  /ip traffic-flow target print
  /ip traffic-flow target enable 0
  ```
- Verificación: `/ip traffic-flow target print detail`

## docker-compose.yml (stack de monitoreo)
```yaml
version: "3.8"

services:

  netflow2ng:
    image: synfinatic/netflow2ng:latest
    container_name: netflow2ng
    restart: unless-stopped
    entrypoint: /netflow2ng
    network_mode: host

  redis:
    image: redis:alpine
    container_name: redis
    restart: unless-stopped
    network_mode: host

  ntopng:
    image: ntop/ntopng:latest
    container_name: ntopng
    restart: unless-stopped
    network_mode: host
    depends_on:
      - netflow2ng
      - redis
    command:
      - "--community"
      - "--redis"
      - "localhost"
      - "--interface"
      - "tcp://localhost:5556"
      - "--local-networks"
      - "192.168.88.0/24"
```

**Por qué `network_mode: host` en los tres servicios**: con NAT de Docker
(el modo bridge default), el puerto de origen de los paquetes NetFlow
entrantes cambia y netflow2ng no los puede procesar. `host` hace que los
contenedores compartan la pila de red de la notebook directamente, sin NAT.

Consecuencia práctica: `EXPOSE` en un Dockerfile no tiene ningún efecto real
de red (es solo metadata/documentación); con `network_mode: host` tampoco
hace falta `ports:` en el compose, porque no hay nada que mapear — el
proceso abre el puerto directo en la interfaz del host.

## Estado actual (confirmado funcionando)
- Pipeline completo probado end-to-end: tráfico generado (ping) desde la
  notebook y desde la segunda PC aparece correctamente diferenciado por IP
  en ntopng.
- Verificación de llegada de paquetes NetFlow crudos antes de levantar
  Docker: `sudo tcpdump -i <interfaz> udp port 2055`.
- Para escanear puertos del stack (UDP 2055 de netflow2ng, TCP 3000 de
  ntopng, TCP 5556 de ZMQ) hay que apuntar nmap a la **IP de la notebook**,
  no a la del Mikrotik (el router solo envía NetFlow, no escucha nada ahí):
  ```
  nmap -sU -p 2055 localhost
  nmap -p 3000,5556 localhost
  ```

## Estructura de carpetas del proyecto
```
proyectoNoc/
├── scriptMk/          # scripts de automatización RouterOS (Loop Protect, etc.)
└── ntopng-stack/       # docker-compose.yml de este stack
```
Actualmente solo carpeta local, sin repo git todavía.

## Próximos pasos posibles
- Explorar vistas de ntopng (Hosts, Flows, protocolos vía nDPI).
- Sumar port mirroring en el RB2011 (`/interface ethernet switch`) +
  Suricata como IDS, para cubrir tráfico entre dispositivos que no rutea
  a través del router (mismo segmento L2, no capturado por NetFlow).
- Documentar el proyecto en GitHub como parte del portfolio.
- Retomar en paralelo el "Packet Visualizer" (FastAPI + Scapy + WebSockets),
  que sí es código propio y en algún momento ameritará un Dockerfile a medida.
