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
from tinyrpc.exc import RPCError

from pyutil import rpc

def handler(signum, frame):
    print os.strerror(errno.ETIMEDOUT)
    os._exit(1)

def get_max_width(table, index):
    return max([len(row[index]) for row in table])

def pretty_print_table(table):
    col_paddings = []

    for i in range(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for row in table:
        print row[0].ljust(col_paddings[0] + 1),
        for i in range(1, len(row)):
            col = row[i].rjust(col_paddings[i] + 2)
            print col,
        print "\n",

def format_app_string(app_id, app_string):
    output = app_string + "(" + str(app_id) + ")"
    return output

class natAddAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"nat_add", "mode": values[0], "ndips": int(values[1]), "sports": int(values[2]), "dports": int(values[3])}
        reply = remote_server.natAdd(**params)

class natAddOneAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"nat_add_one", "sip": values[0], "sport": int(values[1]), "dip": values[2], "dport": int(values[3])}
        reply = remote_server.natAddOne(**params)

class natDelAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"nat_del", "osip": values[0], "odip": values[1], "msip": values[2], "sport": int(values[3]), "dport": int(values[4])}
        reply = remote_server.natDel(**params)

class natCheckAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values:
            params = {"debug":"nat_check", "nports": int(values[0])}
        else:
            params = {"debug":"nat_check", "nports": 0}
        reply = remote_server.natCheck(**params)

class natDumpDepthAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"nat_dump_depth"}
        reply = remote_server.natDumpDepth(**params)
        output = []
        output.append(["BUCKET", "DEPTH"])
        for entry in reply:
            output.append([ str(entry["bucket"]), str(entry["depth"]) ])
        pretty_print_table(output)

class natDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"nat_dump", "dip": values[0], "dir": values[1]}
        reply = remote_server.natDump(**params)
        output = []
        output.append(["TYPE", "OSIP", "ODIP", "OSPORT", "ODPORT", "OPROTO", 
				"MSIP", "MDIP", "MSPORT", "MDPORT", "MPROTO", "2TABLES"])
        for entry in reply:
            orig = entry["Original"]
            mod = entry["Modified"]
	    output.append([ entry["Type"], orig["sip"], orig["dip"], str(orig["sport"]),
			    str(orig["dport"]), str(mod["protocol"]), mod["sip"], mod["dip"],
			    str(mod["sport"]), str(mod["dport"]), str(mod["protocol"]), str(entry["2tables"]) ])	
	pretty_print_table(output)

# Timeout: None == default(2), <= 0 means block forever
rpc_client = rpc.get_local_rpc_client(None, 'tcp://127.0.0.1:46465',
                                      log_requests=False, timeout=None)  # FIXME
remote_server = rpc_client.get_proxy()

parser = argparse.ArgumentParser(description='Debug dump from natd')

parser.add_argument('--nat_dump', action=natDumpAction, nargs=2, metavar=('[all | dest-ip]', '[orig | mod]'), help='Dump NAT info tbl')
parser.add_argument('--nat_add', action=natAddAction, nargs=4, help='Add NAT entries (simulation/UT)')
parser.add_argument('--nat_add_one', action=natAddOneAction, nargs=4, help='Add NAT entries (simulation/UT)')
parser.add_argument('--nat_del', action=natDelAction, nargs=5, help='Del NAT entries (simulation/UT)')
parser.add_argument('--nat_check', action=natCheckAction, nargs=1, help='Run NAT consistency checker')
parser.add_argument('--nat_dump_depth', action=natDumpDepthAction, nargs=0, help='Dump NAT hash table depth')

signal.signal(signal.SIGALRM, handler)
signal.alarm(3)

try:
    args = parser.parse_args()
    sys.exit(0)
except rpc.CommunicationError as e:
    print "Server was not listening"
    sys.exit(1)
except RPCError as e:
    print "RPC error: ", e
    sys.exit(1)
