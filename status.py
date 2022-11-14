#!/usr/bin/env python3

import time
import json
import os
import sys
from datetime  import datetime
import psutil
import netifaces

def get_net():
    nics = []

    for nic in netifaces.interfaces():
        if nic == "lo": continue

        addr = netifaces.ifaddresses(nic)

        if 2 in addr:
            nics.append(nic + " " + addr[2][0]['addr'])
        else:
            nics.append(nic + " (no ipv4)")

    return " | ".join(nics)

def get_battery():
    bat = psutil.sensors_battery()

    if bat.power_plugged:
        prefix = "CHG"
    else:
        prefix = "BAT"

    return "%s: %.2f%%" % (prefix, bat.percent)

def get_status():
    return [
        get_net(),
        get_battery(),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]

while True:
    sys.stdout.write(" | ".join(get_status()))
    sys.stdout.flush()
    time.sleep(5)
