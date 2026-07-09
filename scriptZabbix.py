import requests
from pyzabbix import ZabbixMetric, ZabbixSender

NTOPNG_URL = "http://localhost:3000/lua/rest/v2/get/host/custom_data.lua"
NTOPNG_USER = "admin"
NTOPNG_PASS = "Dgsri2026"   # después lo movemos a variable de entorno

ZABBIX_SERVER = "localhost"
ZABBIX_HOST = "MK HOMELAB"   # el nombre EXACTO del host configurado en Zabbix


def get_top_talkers(top_n=5):
    # 1. hacer el POST a ntopng (el mismo que probamos con curl)
    # 2. filtrar IPs link-local (fe80) y multicast (ff02)
    # 3. ordenar por tx+rx descendente
    # 4. devolver los primeros top_n
    pass


def send_to_zabbix(top_talkers):
    # por cada host del top, armar un ZabbixMetric con:
    #   - ZABBIX_HOST (el nombre del host en zabbix)
    #   - una key tipo "top_talker[1,ip]" / "top_talker[1,bytes]"
    #   - el valor correspondiente
    # después ZabbixSender(ZABBIX_SERVER).send([...metrics...])
    pass


if __name__ == "__main__":
    talkers = get_top_talkers()
    send_to_zabbix(talkers)
