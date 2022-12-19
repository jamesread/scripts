#!/usr/bin/env python3

import time
import requests
import re
import json
import os
import sys
from datetime  import datetime
import psutil
import netifaces
import alsaaudio
import tasklib

tw = tasklib.TaskWarrior()

class ComponentStatus:
    color = ""
    background = ""
    full_text = ""
    name = ""

    def bad(self):
        self.background = "#fa8072"
        self.color = "#000000"

    def good(self):
        self.background = "#90ee90"
        self.color = "#000000"

    def warn(self):
        self.background = "#ffa500"
        self.color = "#000000"


def get_tasks():
    ret = ComponentStatus()

    count = len(tw.tasks.pending().filter('modified < -3d'))

    if count > 30:
        ret.bad()
    else:
        ret.good()
    
    ret.full_text = "Tasks needing update: " + str(count)

    return ret


def get_audio():
    ret = ComponentStatus()

    m = alsaaudio.Mixer()

    if m.getmute()[0] == 1:
        ret.full_text = "muted"
        ret.good()
    else:
        ret.full_text = "Vol: " + str(m.getvolume()[0]) + "%"

    return ret

def get_net():
    ret = ComponentStatus()

    nics = []

    for nic in netifaces.interfaces():
        if nic == "lo": continue

        addr = netifaces.ifaddresses(nic)

        if 2 in addr:
            nics.append(nic + " " + addr[2][0]['addr'])
        else:
            nics.append(nic + " (no ipv4)")

    ret.full_text = " | ".join(nics)

    return ret

def get_battery():
    ret = ComponentStatus()

    bat = psutil.sensors_battery()

    if bat.power_plugged:
        prefix = "CHG"
    else:
        prefix = "BAT"

    ret.full_text = "%s: %.2f%%" % (prefix, bat.percent)

    if bat.percent < 10: ret.bad()
    elif bat.percent < 50: ret.warn()
    else: ret.good()

    return ret

def get_time():
    ret = ComponentStatus()
    ret.full_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return ret

def get_triage():
    return get_prom_metric('gmail_Label_33_total', 'Mail Triage')

def get_inbox_unread():
    return get_prom_metric('gmail_INBOX_unread', 'Mail Unread')

def get_prom_metric(metric, title):
    ret = ComponentStatus()

    try: 
        txt = requests.get("http://localhost:8080/").text
        m = re.search(metric + ' (\d+)', txt)
        v = int(m.groups()[0])

        ret.full_text = title + ': ' + str(v)

        if v > 50:
            ret.bad()
        elif v > 30:
            ret.warn()
        else:
            ret.good()
    except:
        ret.full_text = title + ': error'
        ret.bad()


    return ret

def get_status():
    components = []

    sys.stdout.write("[")

    for cb in callbacks:
        res = cb()
        res.name = cb.__name__

        components.append(json.dumps(res.__dict__))

    sys.stdout.write(",".join(components) + "],")

sys.stdout.write("{ 'version': 1 }\n")
sys.stdout.write('[')
sys.stdout.write("[],")

callbacks = [
    get_net,
    get_tasks,
    get_battery,
    get_audio,
    get_triage,
    get_inbox_unread,
    get_time,
]

while True:
    get_status()
    sys.stdout.flush()
    time.sleep(5)
