#!/usr/bin/python

import sys
import os.path
sys.path.insert(0, '/opt/vc/lib/python')
# Source tree:
sys.path.insert(1, os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../common/pylibs'))

import errno
import os
import signal
import commands
import argparse
import json
import subprocess
import fcntl
import operator
from tinyrpc.exc import RPCError
import re
from pyutil import rpc
from pyutil import pki

def handler(signum, frame):
    print os.strerror(errno.ETIMEDOUT)
    os._exit(1)

# Timeout: None == default(2), <= 0 means block forever
rpc_client = rpc.get_local_rpc_client(None, 'tcp://127.0.0.1:46464',
                                      log_requests=False, timeout=None)
remote_server = rpc_client.get_proxy()

parser = argparse.ArgumentParser(description='tcpdump for dpdk')

parser.add_argument('--tcpdump', action='store', nargs=1, metavar=('[on | off]'), help='on or off')
parser.add_argument('--intf', action='store', nargs=1, help='interface name')
parser.add_argument('--proto', action='store', nargs=1, help='protocol')
parser.add_argument('--proto_e', action='store', nargs=1, help='EXCLUDE protocol')
parser.add_argument('--etype', action='store', nargs=1, help='ethertype')
parser.add_argument('--etype_e', action='store', nargs=1, help='EXCLUDE ethertype')
parser.add_argument('--sports', action='store', nargs='+', help='one or more source ports space seperated [p1 p2 ... pn]')
parser.add_argument('--sports_e', action='store', nargs='+', help='EXCLUDE one or more source ports space seperated [p1 p2 ... pn]')
parser.add_argument('--dports', action='store', nargs='+', help='one or more dest ports space seperated [p1 p2 ... pn]')
parser.add_argument('--dports_e', action='store', nargs='+', help='EXCLUDE one or more dest ports space seperated [p1 p2 ... pn]')
parser.add_argument('--length', action='store', nargs='+', help='length or length range space seperated [start end]')
parser.add_argument('--length_e', action='store', nargs='+', help='EXCLUDE length or length range space seperated [start end]')

signal.signal(signal.SIGALRM, handler)
signal.alarm(20)

try:
    args = parser.parse_args()
    if not args.tcpdump:
        print "Need a --tcpdump on|off at the minimum\n"
        sys.exit(0)
    tcpdump = args.tcpdump[0]
	
    if not args.intf:
        intf = "anyinterface"
    else:
        intf = args.intf[0]

    proto_str = "proto"
    proto = "none"        
    if args.proto: 
        proto_str = "proto"    
        proto = args.proto[0]
    if args.proto_e:
        proto_str = "proto_e"    
        proto = args.proto_e[0]

    etype_str = "etype"
    etype = "none"
    if args.etype:
        etype_str = "etype"
        etype = args.etype[0]
    if args.etype_e:
        etype_str = "etype_e"
        etype = args.etype_e[0]

    sports = []
    sports_str = "sports"
    if args.sports:
        sports_str = "sports"
        for p in args.sports:
            sports.append(int(p))
    if args.sports_e:
        sports_str = "sports_e"
        for p in args.sports_e:
            sports.append(int(p))

    dports = []
    dports_str = "dports"
    if args.dports:
        dports_str = "dports"
        for p in args.dports:
            dports.append(int(p))
    if args.dports_e:
        dports_str = "dports_e"
        for p in args.dports_e:
            dports.append(int(p))

    length = []
    length_str = "length"        
    if args.length:
        length_str = "length"        
        for l in args.length:
            length.append(int(l))
    if args.length_e:
        length_str = "length_e"        
        for l in args.length_e:
            length.append(int(l))

    params = {"debug":"tcpdump", "tcpdump":tcpdump, "intf": intf, proto_str: proto, etype_str: etype, sports_str: sports, dports_str: dports, length_str : length}
    print params 
    reply = remote_server.TcpDump(**params)
except rpc.CommunicationError as e:
    print "Server was not listening"
    sys.exit(1)
except RPCError as e:
    print "RPC error: ", e
    sys.exit(1)
