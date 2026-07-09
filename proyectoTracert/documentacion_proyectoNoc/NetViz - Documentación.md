# NetViz — Fase 1

**Backend de traceroute con enriquecimiento MAC y vendor.**

Proyecto Python que realiza traceroute por ICMP y, por cada hop, resuelve:
- IP y hostname (DNS reverso)
- MAC address (ARP local) y fabricante (OUI)
- RTT de cada salto

Todo se transmite en **tiempo real vía WebSocket**.

[[Arquitectura]] · [[main.py]] · [[tracer.py]] · [[test_client.py]] · [[Referencia API]]
