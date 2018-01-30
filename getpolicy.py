#!/usr/bin/python

# Usage: getpolicy.py policymodule

import sys
import os.path
import argparse
import json

# Parse arguments
parser = argparse.ArgumentParser(description="Retrieve a section of policy")
parser.add_argument('policymodule', help="policy module to print in dotted notation, e.g. managementPlane or managementPlane.data.managementPlaneProxy", nargs=1)
args = parser.parse_args()

# NOTE: getpolicy.py can also be called using the top-level keys under
# edge.info. For example, to get the "edgeInfo" structure, call
# getpolicy.py edgeInfo.

# config walking code:
MGDCONFIG = "/etc/config/mgd"
CONFIGPAT = "/opt/vc/.%s.info"

def get_config_name():
    try:
        with open(MGDCONFIG, "r") as f:
            mgdcfg = json.load(f)
        devtype = mgdcfg.get("mgd", {}).get("device", "edge")
    except:
        devtype = "edge"
    return CONFIGPAT % devtype

def load_config():
    cfgfilename = get_config_name()
    # print cfgfilename
    try:
        with open(cfgfilename, "r") as f:
            return json.load(f)
    except:
        return {}

info = load_config()
#print json.dumps(info)
m = args.policymodule[0]
if m in info:
    print json.dumps(info.get(m, {}), indent=1)
    sys.exit(0)

cfg = info.get("configuration", {})
modules = m.split(".")
path = ""
for module in modules:
    if module not in cfg:
        sys.exit(0)
    else:
        cfg = cfg[module]

print json.dumps(cfg,indent=1)
