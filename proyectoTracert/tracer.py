"""
Módulo de descubrimiento de red.

Hace un traceroute manual con paquetes ICMP (TTL incremental) y, para cada
hop descubierto, intenta resolver la MAC address mediante ARP si el hop
pertenece a la misma subred que la interfaz local.

Esto se ejecuta con privilegios de root (necesario para raw sockets).
"""

import socket
import time
import ipaddress
from dataclasses import dataclass, asdict
from typing import Optional, AsyncIterator

from scapy.all import IP, ICMP, sr1, ARP, Ether, srp, conf
from manuf import manuf

# Parser de OUI (fabricante) - se carga una sola vez
_MAC_PARSER = manuf.MacParser()

MAX_HOPS = 30
TIMEOUT = 2  # segundos por intento de ICMP
ARP_TIMEOUT = 1  # segundos por intento de ARP


@dataclass
class HopResult:
    ttl: int
    ip: Optional[str]
    hostname: Optional[str]
    rtt_ms: Optional[float]
    mac: Optional[str]
    vendor: Optional[str]
    mac_scope: str  # "local" | "gateway" | "unavailable"
    is_destination: bool
    timed_out: bool

    def to_dict(self):
        return asdict(self)


def _resolve_hostname(ip: str) -> Optional[str]:
    """Resolución DNS inversa. Devuelve None si no hay PTR record."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror, OSError):
        return None


def _get_local_network() -> Optional[ipaddress.IPv4Network]:
    """
    Determina la subred local de la interfaz que Scapy usaría por defecto
    (la que tiene la ruta hacia internet / la red principal).
    """
    try:
        iface = conf.iface
        ip_str = conf.route.route("0.0.0.0")[1]  # IP local de salida
        # Buscamos la máscara de esa interfaz en la tabla de rutas de Scapy
        for net, mask, gw, ifname, addr, metric in conf.route.routes:
            if ifname == iface.name and addr == ip_str and net != 0:
                network = ipaddress.IPv4Network((net, mask), strict=False)
                return network
        # Fallback: asumimos /24 sobre la IP local
        return ipaddress.IPv4Network(f"{ip_str}/24", strict=False)
    except Exception:
        return None


def _arp_lookup(ip: str) -> tuple[Optional[str], Optional[str]]:
    """
    Envía un ARP request a una IP en la LAN local.
    Devuelve (mac, vendor) o (None, None) si no responde.
    """
    try:
        pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip)
        answered, _ = srp(pkt, timeout=ARP_TIMEOUT, verbose=0, retry=1)
        if answered:
            mac = answered[0][1].hwsrc
            vendor = _MAC_PARSER.get_manuf(mac) or "Desconocido"
            return mac, vendor
    except Exception:
        pass
    return None, None


def _get_gateway_mac() -> tuple[Optional[str], Optional[str]]:
    """MAC del gateway de salida local, usado como referencia para hops WAN."""
    try:
        gw_ip = conf.route.route("0.0.0.0")[2]
        if gw_ip and gw_ip != "0.0.0.0":
            return _arp_lookup(gw_ip)
    except Exception:
        pass
    return None, None


def run_traceroute(target: str, max_hops: int = MAX_HOPS) -> list[HopResult]:
    """
    Versión síncrona y generadora-friendly: devuelve la lista completa.
    (La versión streaming para WebSocket está en run_traceroute_stream).
    """
    return list(run_traceroute_stream(target, max_hops))


def run_traceroute_stream(target: str, max_hops: int = MAX_HOPS):
    """
    Generador que produce un HopResult por cada TTL, en orden, listo para
    pushear por WebSocket a medida que se descubre cada salto.
    """
    try:
        dest_ip = socket.gethostbyname(target)
    except socket.gaierror:
        yield HopResult(
            ttl=0, ip=None, hostname=None, rtt_ms=None,
            mac=None, vendor=None, mac_scope="unavailable",
            is_destination=False, timed_out=True,
        )
        return

    local_net = _get_local_network()
    gw_mac, gw_vendor = None, None  # se resuelve lazy, solo si hace falta

    for ttl in range(1, max_hops + 1):
        pkt = IP(dst=dest_ip, ttl=ttl) / ICMP()
        start = time.time()
        reply = sr1(pkt, timeout=TIMEOUT, verbose=0)
        elapsed_ms = round((time.time() - start) * 1000, 2)

        if reply is None:
            yield HopResult(
                ttl=ttl, ip=None, hostname=None, rtt_ms=None,
                mac=None, vendor=None, mac_scope="unavailable",
                is_destination=False, timed_out=True,
            )
            continue

        hop_ip = reply.src
        hostname = _resolve_hostname(hop_ip)
        is_dest = (hop_ip == dest_ip)

        # Estrategia de MAC según el escenario
        mac, vendor, scope = None, None, "unavailable"

        in_local_net = local_net is not None and ipaddress.ip_address(hop_ip) in local_net

        if in_local_net:
            mac, vendor = _arp_lookup(hop_ip)
            scope = "local" if mac else "unavailable"
        else:
            # Hop fuera de la LAN local -> usamos la MAC del gateway de salida
            if gw_mac is None and gw_vendor is None:
                gw_mac, gw_vendor = _get_gateway_mac()
            mac, vendor = gw_mac, gw_vendor
            scope = "gateway" if mac else "unavailable"

        yield HopResult(
            ttl=ttl,
            ip=hop_ip,
            hostname=hostname,
            rtt_ms=elapsed_ms,
            mac=mac,
            vendor=vendor,
            mac_scope=scope,
            is_destination=is_dest,
            timed_out=False,
        )

        if is_dest:
            break
