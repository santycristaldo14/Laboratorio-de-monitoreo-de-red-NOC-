#!/bin/bash
# Crea la red compartida entre ntopng-stack y zabbix-stack.
# Correr una sola vez antes de levantar cualquiera de los dos stacks.
#
# Uso:
#   chmod +x setup-network.sh
#   ./setup-network.sh

if docker network inspect monitoring-net >/dev/null 2>&1; then
  echo "La red 'monitoring-net' ya existe, no se crea de nuevo."
else
  docker network create monitoring-net
  echo "Red 'monitoring-net' creada."
fi
