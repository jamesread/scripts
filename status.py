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
from prometheus_api_client import PrometheusConnect

tw = tasklib.TaskWarrior()
promcon = PrometheusConnect(url='http://prom.webapps.teratan.lan', disable_ssl=True)

atHome = False

class ComponentStatus:
    color = ""
    background = ""
    full_text = ""
    name = ""

    def set(self, bg, fg, text = None):
        self.background = bg
        self.color = fg

        if text != None:
            self.full_text = text

        return self

    def no_result(self, text = None):
        return self.set("#000000", "#ffffff", text)

    def bad(self, text = None):
        return self.set("#fa8072", "#000000", text);

    def good(self, text = None):
        return self.set("#90ee90", "#000000", text)

    def warn(self, text = None):
        return self.set("#ffa500", "#000000", text)

def get_prom_metric(metric, title):
    ret = ComponentStatus()

    if not atHome:
        ret.no_result('!home')
        return ret

    try:
        v = int(promcon.get_current_metric_value(metric_name=metric, timeout=3)[0]['value'][1])
    except:
        ret.no_result()
        v = -1

    if v > 50:
        ret.bad()
    elif v > 30:
        ret.warn()
    elif v > 0:
        ret.good()

    ret.full_text = "%s: %s" % (title, v)

    return ret

def get_prom_metric_old(metric, title):
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


def get_tasks():
    ret = ComponentStatus()

    try:
        count = len(tw.tasks.pending().filter('modified < -3d'))
    except:
        ret.bad('tasklib exception')
        return ret

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
        ret.good("muted")
    else:
        ret.full_text = "Vol: " + str(m.getvolume()[0]) + "%"

    return ret

def get_net():
    ret = ComponentStatus()

    nics = []

    for nic in netifaces.interfaces():
        if nic == "lo": continue
        if "docker" in nic: continue
        if "br-" in nic: continue
        if "virbr" in nic: continue
        if "podman" in nic: continue
        if "veth" in nic: continue

        addr = netifaces.ifaddresses(nic)

        IPV4 = 2

        if IPV4 in addr:
            addr = addr[IPV4][0]['addr']

            if "192.168.66" in addr:
                atHome = True

            nics.append(nic + ": " + addr)
        else:
            nics.append(nic + ": !ipv4")

    ret.full_text = " | ".join(nics)

    return ret

def get_battery():
    ret = ComponentStatus()

    bat = psutil.sensors_battery()

    if bat == None:
        ret.full_text = "PSU"
    else:
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

def get_status():
    components = []

#    sys.stdout.write("[")

    for cb in callbacks:
        try:
            res = cb()
        except e:
            print(e)
            res = ComponentStatus()
            res.bad(cb.__name__ + ': exception')

        res.name = cb.__name__

        components.append(res.__dict__)

    return json.dumps(components)

callbacks = [
    get_net,
    get_battery,
    get_audio,
    get_inbox_unread,
    get_triage,
    get_tasks,
    get_time,
]

if "wayland" in os.getenv('XDG_SESSION_TYPE'):
    sys.stdout.write("{ 'version': 1 }\n")
    sys.stdout.write('[')
    sys.stdout.write("[{'full_text': 'waiting for first run...'}]")

    while True:
        sys.stdout.write("," + get_status())
        sys.stdout.flush()
        time.sleep(5)
else:
    with os.popen("/usr/bin/i3status", mode="r", buffering=1) as status:
        while True:
            sys.stdout.flush()
            line = status.readline()

            if line == "": break

            if not line.startswith(","):
                print(line.strip())
                continue

            parsed = json.loads(line[1:])
            print(",%s" % get_status())
            time.sleep(5)

