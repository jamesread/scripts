#!/usr/bin/python

from fabric.api import *
from pyparsing import *
import datetime, time
import sys
import re
import getpass

def dhcpdLeases():
        f = open('/var/lib/dhcpd/dhcpd.leases', 'rb')

        addresses = set()

        for line in f:
                if "lease" in line:
                        queued = line.replace("lease", "").replace("{", "").strip()
                elif "ends" in line:
                        # eg: 2014/03/13 16:22:26
                        ends = time.strptime(re.sub(r"ends \d", "", line).strip(), "%Y/%m/%d %H:%M:%S;")

                        if ends > time.localtime():
                                addresses.add(queued)
                                print "Active lease: ", queued

        return addresses;

env.disable_known_hosts = True
env.hosts = dhcpdLeases()
env.password = getpass.getpass("Password:")

@parallel
def uptime():
        run("uptime")

