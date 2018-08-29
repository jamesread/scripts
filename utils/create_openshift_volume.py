#!/usr/bin/python

import sys
import os.path
import argparse
import tempfile
from subprocess import call

parser = argparse.ArgumentParser();
parser.add_argument("path")
parser.add_argument("--pv", default = False, action = 'store_true')
parser.add_argument("--pvc", default = False, action = 'store_true')
args = parser.parse_args();

def parsePath(path):
  if not os.path.exists(path):
    sys.exit("That doesn't even exist yet.")

  namespace = os.path.basename(os.path.dirname(path))
  volumeName = os.path.basename(path)
  
  print "namespace: ", namespace
  print "volumeName: ", volumeName
  print

  return namespace, volumeName

def promptToContinue():
  try: 
    shouldWeContinue = raw_input("Does this look OK? (Y to continue, or Control+C/N to quit): ").lower().strip() == "y"
  except KeyboardInterrupt:
    shouldWeContinue = False

  print "-" * 30
  print 

  if not shouldWeContinue: 
    sys.exit("Okay then, bye!")

def setupVolumeDirectory(path):
  os.chmod(path, 0777)

def addVolumeToNfsExports(path, namespace, volumeName):
  handle = open("/etc/exports.d/" + namespace + "-" + volumeName + ".exports", 'w')

  line = path + " *(rw)\n" 

  handle.write(line);
  handle.close()

def createPvDefinition(path, namespace, volumeName):
  templateHandle = open("../examples/openshift-pv-nfs.yml", "r");

  contents = templateHandle.read()
  contents = contents.replace("VOLUME_NAME", volumeName)
  contents = contents.replace("NAMESPACE", namespace)
  contents = contents.replace("PATH", path)

  ocCreate(contents)

def createPvcDefinition(namespace, volumeName):
  templateHandle = open("../examples/openshift-pvc.yml", "r");

  contents = templateHandle.read()
  contents = contents.replace("VOLUME_NAME", volumeName)
  contents = contents.replace("NAMESPACE", namespace)

  ocCreate(contents)


def ocCreate(contents):
  foo, tmpFilename = tempfile.mkstemp();

  tmpHandle = open(tmpFilename, 'w')
  tmpHandle.write(contents)
  tmpHandle.close()
  
  call(["oc", "create", "-f", tmpFilename])
  
  print tmpFilename

#  os.remove(tmpFilename)


def main(args):
  namespace, volumeName = parsePath(args.path);

  promptToContinue()

  setupVolumeDirectory(args.path)
  addVolumeToNfsExports(args.path, namespace, volumeName)
  
  if args.pv:
    createPvDefinition(args.path, namespace, volumeName)

  if args.pvc:
    createPvcDefinition(namespace, volumeName)

  print "You should manually restart NFS."

###
main(parser.parse_args());
