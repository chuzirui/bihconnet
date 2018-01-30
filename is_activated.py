#!/usr/bin/python

# Usage: python is_activated

# Writes 'True' if the device has been activated, else 'False'.
# If the activation is in a "waiting-for-software-update" state
# (i.e. not fully activated), the script will write 'Partial'.

import json
import os

CONFFILE="/opt/vc/.edge.info"

try:
    with open("/etc/config/mgd", "r") as f:
        mgdconf = json.load(f)
    if mgdconf.get('mgd', {}).get('device') == 'gateway':
        CONFFILE="/opt/vc/.gateway.info"
except:
    pass

ACTCONFFILE="%s.activation" % CONFFILE

if os.access(CONFFILE, os.R_OK):
    CFILE=CONFFILE
elif os.access(ACTCONFFILE, os.R_OK):
    CFILE=ACTCONFFILE
else:
    CFILE=None

c = {}
try:
    if CFILE:
        with open(CFILE, "r") as f:
            c = json.load(f)
except:
    pass

activated = c.get('activated', False)
if not activated:
    pending_update = c.get('pending_update', False)
else:
    pending_update = False

if pending_update:
    print "Partial"
else:
    print activated
