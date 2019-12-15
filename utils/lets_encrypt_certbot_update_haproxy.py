#!/usr/bin/env python3

from os import scandir
from os.path import isdir, join
from urllib.request import urlopen

def getDomains():
    for ent in scandir("/etc/letsencrypt/live"):
        if isdir(ent):
            yield ent

for domain in getDomains():
    fullchain = open(join(domain, "fullchain.pem")).read()
    privkey = open(join(domain, "privkey.pem")).read()

    print("Updating: ", domain.name);

    haproxyPem = open("/etc/haproxy/certs/" + domain.name + ".pem", 'w');
    haproxyPem.write(fullchain);
    haproxyPem.write(privkey);
    haproxyPem.close()
