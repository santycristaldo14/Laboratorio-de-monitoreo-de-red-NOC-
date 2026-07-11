import requests
from pyzabbix import ZabbixMetric, ZabbixSender

import os
from dotenv import load_dotenv

load_dotenv()

NTOPNG_URL = "http://localhost:3000/lua/rest/v2/get/host/custom_data.lua"
NTOPNG_USER = os.getenv("NTOPNG_USER")
# después lo movemos a variable de entorno
NTOPNG_PASS = os.getenv("NTOPNG_PASS")

ZABBIX_SERVER = os.getenv("ZABBIX_SERVER")
# el nombre EXACTO del host configurado en Zabbix
ZABBIX_HOST = os.getenv("ZABBIX_HOST")


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
    metrics = []
    for i, host in enumerate(top_talkers, start=1):
        key_ip = f"top_talker[{i},ip]"
        key_bytes = f"top_talker[{i},bytes]"
        metrics.append(ZabbixMetric(ZABBIX_HOST, key_ip, host["ip"]))
        metrics.append(ZabbixMetric(
            ZABBIX_HOST, key_bytes, host["tx"] + host["rx"]))

    print("CANTIDAD DE METRICS:", len(metrics))
    for m in metrics:
        print(m.__dict__)

    result = ZabbixSender(ZABBIX_SERVER).send(metrics)
    print(result)


if __name__ == "__main__":
    talkers = get_top_talkers()
    send_to_zabbix(talkers)
