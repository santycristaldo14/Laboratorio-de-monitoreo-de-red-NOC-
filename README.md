# Laboratorio de Monitoreo de Red - NOC

Stack de monitoreo y detección de tráfico de red en laboratorio, usando un
Mikrotik RB2011 como fuente de datos. Proyecto de portfolio orientado a
NOC / seguridad de redes, pensado como puente entre administración de redes
on-premise y conceptos que después se trasladan a entornos cloud (AWS).

## Arquitectura general

```
                                ┌──> netflow2ng ──> ntopng (dashboard tráfico, :3000)
                                │
Mikrotik RB2011 ────────────────┼──> SNMP ──> Zabbix (salud + top talkers, :8081)
   (aislado de la red de       │
    producción para pruebas)   └──> Mirror port (WAN) ──> Suricata (IDS)
                                         │
                                         └──> eve.json ──> Promtail ──> Loki ──> Grafana (:3001)
```

Todos los servicios corren en Docker Compose sobre una notebook con Arch
Linux. `netflow2ng`, `ntopng`, `redis` y `suricata` usan `network_mode: host`
por requisitos técnicos de captura de red (ver sección "Decisiones técnicas
y aprendizajes" más abajo).

## Estado actual — qué está funcionando

### 1. NetFlow + ntopng
- El Mikrotik exporta NetFlow v9 (`/ip traffic-flow`) hacia la notebook.
- `netflow2ng` traduce el NetFlow crudo a ZMQ, que consume `ntopng`.
- Dashboard de tráfico en tiempo real, con hosts, flows y protocolos (nDPI).
- Volúmenes persistentes (`ntopng_data`, `redis_data`) para que la
  configuración sobreviva a reinicios.

### 2. Zabbix + SNMP + Top Talkers
- Mikrotik expone SNMP (`/snmp`), Zabbix lo scrapea con el template
  `Mikrotik by SNMP` (tráfico por interfaz, CPU, memoria, uptime).
- Script propio en Python (`scriptZabbix.py`) que consulta la REST API de
  ntopng (`/lua/rest/v2/get/host/custom_data.lua`), calcula el top 5 de
  hosts por consumo (`tx+rx`), filtra IPs link-local/multicast, y envía los
  resultados a Zabbix como **trapper items** (`top_talker[N,ip]` /
  `top_talker[N,bytes]`) vía `pyzabbix`.
- Corre nativo en la notebook (no containerizado todavía).

### 3. Suricata (IDS) + mirror port
- Mirror port configurado en el switch chip del Mikrotik
  (`/interface ethernet switch`, `mirror-source=ether1` [WAN],
  `mirror-target=ether4` [notebook]) — ambos puertos confirmados en el
  mismo switch group (`switch1`).
- Interfaz de la notebook en modo promiscuo para capturar el tráfico
  espejado.
- Suricata corriendo con el ruleset **ET Open** (52.018 reglas activas,
  actualizadas vía `suricata-update`).
- Regla de supresión aplicada (`threshold.config`) para silenciar ruido de
  la signature `SURICATA Ethertype unknown` (sid 2200121), de bajo valor.
- Confirmado con tráfico real: la firma `GPL ATTACK_RESPONSE id check
  returned root` disparó correctamente al probar con `testmyids.com`.

### 4. Logs estructurados: Loki + Promtail + Grafana
- Promtail lee `eve.json` de Suricata y lo envía a Loki.
- Grafana (con Loki como data source) permite explorar y filtrar alertas
  con LogQL, por ejemplo:
  ```
  {job="suricata"} |= `"event_type":"alert"` | json alert_severity="alert.severity", alert_signature="alert.signature", proto="proto", src_ip="src_ip", dest_ip="dest_ip"
  ```
  Esta query con alias explícitos evita tener que usar transformaciones
  de "Labels to fields" en Grafana (que dieron problemas de orden/caché).
- Cada evento de alerta de Suricata también trae embebidos los campos de
  flow asociado (`flow_bytes_toclient`, `flow_bytes_toserver`, etc.), sin
  necesidad de correlación aparte por `flow_id`.

## Pendiente / próximos pasos

- **Dashboard de Suricata en Grafana**: la query LogQL con alias funciona
  bien en modo Explore/panel individual, pero falta pulir la tabla final
  (columnas prolijas: severidad, signature, protocolo, IPs, consumo) y
  guardarla como dashboard persistente.
- **Alertas de Grafana**: configurar una alerta que notifique cuando
  aparezca una signature de severidad alta (1) — no implementado todavía.
- **MAC address en alertas de Suricata**: no viene loguead por default;
  requiere habilitar `ethernet: yes` en la sección `eve-log` de
  `suricata.yaml` si se quiere ese dato en el dashboard.
- **Volumen `/etc/suricata` sin nombre declarado**: actualmente Docker le
  asignó un volumen con hash autogenerado (no un named volume del
  compose). Persiste correctamente, pero conviene declararlo explícito
  (`suricata_config:/etc/suricata`) para que sea más fácil de ubicar.
- **Integración Suricata → ntopng** (companion interface vía syslog):
  evaluada pero descartada por ahora a favor de Loki/Grafana, que ya
  cubre la necesidad de logs estructurados con menor complejidad.
- **Script de top talkers**: sigue corriendo nativo (no containerizado).
  Contenerizarlo es una mejora futura, no urgente.
- **Packet Visualizer** (proyecto hermano, FastAPI + Scapy + WebSockets):
  Fase 1 (backend traceroute/ARP) implementada pero no testeada. Pendiente
  de retomar.

## Decisiones técnicas y aprendizajes

- **`netflow2ng` requiere `network_mode: host`** de forma obligatoria: en
  modo bridge, Docker le hace NAT a los paquetes NetFlow entrantes,
  perdiendo el puerto de origen real y rompiendo la recepción del flujo.
- **Se intentó mover `ntopng`/`redis` a una red bridge separada
  (`monitoring-net`)**, usando `host.docker.internal` para que `ntopng`
  alcance a `netflow2ng` en host networking. El resultado fue que `ntopng`
  quedaba "escuchando" según sus logs, pero no respondía a ninguna
  conexión (ni siquiera desde dentro del propio contenedor a su IP
  interna) — se revirtió la decisión y **`ntopng`/`redis` volvieron a
  `network_mode: host`**, arquitectura más simple y ya validada como
  estable. `monitoring-net` se mantiene solo como concepto para el stack
  de Zabbix/Grafana si se decide separarlos más adelante.
- **ntopng community edition no soporta NetFlow crudo directamente** —
  requiere `netflow2ng` (gratis) o `nProbe` (pago) como intermediario.
- **La imagen oficial `ntop/ntopng` en Docker Hub solo publica el tag
  `latest`**, sin versiones fijas. Esto causó al menos un incidente real
  (actualización silenciosa que dejó de mostrar el dashboard hasta
  recrear el contenedor). Alternativa evaluada: fijar por `@sha256:digest`
  si se necesita estabilidad total, ya que no hay tags numerados
  oficiales.
- **RouterOS `/ip traffic-flow target`**: el parámetro correcto es
  `dst-address` (no `address`), y `src-address` va dentro del mismo
  `target add`, no en el `/ip traffic-flow set` general. Los targets
  nuevos quedan deshabilitados por default.
- **Zabbix trapper item keys con parámetros**: la sintaxis correcta es
  `top_talker[1,ip]` (coma **dentro** de los corchetes). Un error de
  tipeo (`top_talker[1],ip`, coma afuera) generó rechazos silenciosos
  (`failed: 10`) sin mensaje de error claro del lado de Zabbix — se
  diagnosticó comparando contra `zabbix_sender` manual con `-vv`.
- **RB2011 tiene dos switch chips separados** (`switch1`/`switch2`); el
  mirror port solo funciona entre puertos del mismo chip. Hay que
  confirmar con `/interface ethernet switch port print` antes de armar
  el mirror.
- **Elegir WAN como mirror source** da visibilidad de amenazas externas
  (perimetral), pero no ve tráfico interno entre dispositivos de la LAN
  (movimiento lateral). Trade-off consciente para este proyecto.
- **Grafana + Loki, sintaxis de parseo JSON anidado**: para extraer campos
  anidados del `eve.json` de Suricata (ej. `alert.severity`) hay que
  usar alias explícitos en la query LogQL (`| json campo="ruta.anidada"`)
  en vez de depender de las transformaciones automáticas de Grafana
  ("Labels to fields" + "Organize fields by name"), que resultaron
  frágiles ante cambios de query y orden de aplicación.
- **Puertos ocupados a tener en cuenta** en esta notebook:
  `3000` (ntopng), `3001` (Grafana), `3100` (Loki), `8080` (métricas
  internas de netflow2ng), `8081` (Zabbix web), `10051` (Zabbix trapper).

## Estructura del proyecto

```
proyectoNoc/
├── scriptMk/              # scripts de automatización RouterOS
├── ntopng-stack/
│   ├── docker-compose.yml       # netflow2ng, ntopng, redis, suricata, loki, promtail, grafana
│   ├── promtail-config.yaml
│   └── scriptZabbix.py          # top talkers ntopng → Zabbix trapper
├── zabbix-stack/
│   └── docker-compose.yml       # postgres, zabbix-server, zabbix-web
└── setup-network.sh        # crea red compartida (uso actualmente limitado, ver notas arriba)
```

## Seguridad / notas de higiene

- Credenciales (ntopng, Zabbix) manejadas vía variables de entorno
  (`.env`, excluido de git) en vez de hardcodeadas en el script Python.
- Repo público: se revisó que no haya IPs reales de la red de trabajo,
  hostnames internos, ni credenciales antes de publicar.
