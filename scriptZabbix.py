import requests
from pyzabbix import ZabbixMetric, ZabbixSender

NTOPNG_URL = "http://localhost:3000/lua/rest/v2/get/host/custom_data.lua"
NTOPNG_USER = ""
NTOPNG_PASS = ""   # después lo movemos a variable de entorno

ZABBIX_SERVER = "localhost"
ZABBIX_HOST = ""   # el nombre EXACTO del host configurado en Zabbix


def get_top_talkers(top_n=5):
    url = NTOPNG_URL
    payload = {"ifid": 0, "field_alias": "ip,bytes.sent=tx,bytes.rcvd=rx"}
    auth = (NTOPNG_USER, NTOPNG_PASS)

    response = requests.post(url, auth=auth, json=payload)
    data = response.json()["rsp"]

    topTalkers = []
    for host in data:
        if not host["ip"].startswith(("fe80", "ff02")):
            topTalkers.append(host)

    topTalkers = sorted(
        topTalkers, key=lambda h: h["tx"] + h["rx"], reverse=True)

    return topTalkers[:top_n]


def send_to_zabbix(top_talkers):
    # por cada host del top, armar un ZabbixMetric con:
    #   - ZABBIX_HOST (el nombre del host en zabbix)
    #   - una key tipo "top_talker[,ip]" / "top_talker[1,bytes]"
    #   - el valor correspondiente
    # después ZabbixSender(ZABBIX_SERVER).send([...metrics...])
    pass


if __name__ == "__main__":
    talkers = get_top_talkers()
    send_to_zabbix(talkers)
