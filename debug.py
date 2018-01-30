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
import string
from tinyrpc.exc import RPCError
from pyutil import pki
from pyutil import rpc
from operator import attrgetter

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
        print row[0].encode('UTF-8').ljust(col_paddings[0] + 1),
        for i in range(1, len(row)):
            col = row[i].encode('UTF-8').rjust(col_paddings[i] + 2)
            print col,
        print "\n",

class listConEdgesAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"list_edges", "apiVersion":int(values[0])}
        reply = remote_server.listEdgesDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        if values[0] == "3":
            edges = []
            edges.append(["Name", "Enterprise", "Logical ID", "VC Private IP"])
            for entry in reply:
                edges.append([entry["name"], entry["enterprise_id"], entry["vceid"], entry["priv_ip"]])
            pretty_print_table(edges)
        else:
            print json.dumps(reply, sort_keys = True, indent = 2)

class pathStatsDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"path_stats"}
        reply = remote_server.pathStatsDebugDump(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class linkStatsDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"link_stats"}
        reply = remote_server.linkStatsDebugDump(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class peerDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"peers"}
        reply = remote_server.peerDebugDump(**params)
        #print json.dumps(reply, sort_keys = True, indent = 2)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        peers = []
        peers.append(["Enterprise", "EnterpriseID", "Type", "Name", "Destination", "MTU", "Reachable"])
        for entry in reply:
            peertbl = entry["peers"]
            for peer in peertbl:
                peers.append([str(entry["enterprise_name"]), str(entry["enterprise_id"]), peer["type"], str(peer["name"]), peer["destination"], str(peer["mtu"]), str(peer["reachable"])])
        pretty_print_table(peers)

class endpointDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"endpoints"}
        reply = remote_server.endpointDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        endpoints = []
        endpoints.append(["src_ip", "dst_ip", "refcnt"])
        for entry in reply:
            endpoints.append([str(entry["src_ip"]), str(entry["dst_ip"]), str(entry["refcnt"])])
        pretty_print_table(endpoints)

class routeDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"routes"}
        if values:
            if (len(values) == 2):
                params = {"entr": values[0], "dip": values[1]}
            else:
                params = {"entr": values[0], "dip": "all"}
        else:
            params = {"entr": "all", "dip":"all"}
        reply = remote_server.routeDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        routes = []
        routes.append(["EnterpriseID", "Address", "Netmask", "Type", "Destination", "Reachable", "Metric", "Preference", "Flags", "C-Tag", "S-Tag", "Handoff", "Mode", "Age"])
        for entry in reply:
            routetbl = entry["routes"]
            for route in routetbl:
				if str(route["type"]) == "edge2edge":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), "N/A", "N/A", str(route["age_s"])])
				elif str(route["type"]) == "datacenter":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), "0", str(-1), str(-1), "N/A", "N/A", str(route["age_s"])])
				else :
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), str(route["handoff"]), str(route["mode"]), str(route["age_s"])])
        pretty_print_table(routes)
        print "P - PG, B - BGP, D - DCE, L - LAN SR, C - Connected, O - External, W - WAN SR, S - SecureEligible, R - Remote, s - self, H - HA, m - Management, n - nonVelocloud, v - ViaVeloCloud"

class routeNoneDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"routes"}
        reply = remote_server.routeNoneDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        routes = []
        routes.append(["Address", "Netmask", "Type", "Destination", "Reachable", "Metric", "Preference", "Flags", "C-Tag", "S-Tag", "Handoff", "Mode"])
        for route in reply:
            if str(route["type"]) == "edge2edge":
			    routes.append([route["address"], route["netmask"], route["type"],
                route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), "N/A", "N/A"])
            elif str(route["type"]) == "datacenter":
                routes.append([route["address"], route["netmask"], route["type"],
                route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), "0", str(-1), str(-1), "N/A", "N/A"])
            else :
                routes.append([route["address"], route["netmask"], route["type"],
                route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), str(route["handoff"]), str(route["mode"])])
        pretty_print_table(routes)

class routeE2EDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"routes"}
        if values:
            if (len(values) == 2):
                params = {"entr": values[0], "dip": values[1]}
            else:
                params = {"entr": values[0], "dip": "all"}
        else:
            params = {"entr": "all", "dip":"all"}
        reply = remote_server.routeE2EDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        routes = []
        routes.append(["EnterpriseID", "Address", "Netmask", "Type", "Destination", "Reachable", "Metric", "Preference", "Flags", "C-Tag", "S-Tag", "Handoff", "Mode", "Age"])
        for entry in reply:
            routetbl = entry["routes"]
            for route in routetbl:
				if str(route["type"]) == "edge2edge":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), "N/A", "N/A", str(route["age_s"])])
				elif str(route["type"]) == "datacenter":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), "0", str(-1), str(-1), "N/A", "N/A", str(route["age_s"])])
				else :
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), str(route["handoff"]), str(route["mode"]), str(route["age_s"])])
        pretty_print_table(routes)

class routePGDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"routes"}
        if values:
            if (len(values) == 2):
                params = {"entr": values[0], "dip": values[1]}
            else:
                params = {"entr": values[0], "dip": "all"}
        else:
            params = {"entr": "all", "dip":"all"}
        reply = remote_server.routePGDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        routes = []
        routes.append(["EnterpriseID", "Address", "Netmask", "Type", "Destination", "Reachable", "Metric", "Preference", "Flags", "C-Tag", "S-Tag", "Handoff", "Mode", "Age"])
        for entry in reply:
            routetbl = entry["routes"]
            for route in routetbl:
				if str(route["type"]) == "edge2edge":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), "N/A", "N/A", str(route["age_s"])])
				elif str(route["type"]) == "datacenter":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), "0", str(-1), str(-1), "N/A", "N/A", str(route["age_s"])])
				else :
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), str(route["handoff"]), str(route["mode"]), str(route["age_s"])])
        pretty_print_table(routes)

class routeE2DCDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"routes"}
        if values:
            if (len(values) == 2):
                params = {"entr": values[0], "dip": values[1]}
            else:
                params = {"entr": values[0], "dip": "all"}
        else:
            params = {"entr": "all", "dip":"all"}
        reply = remote_server.routeE2DCDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        routes = []
        routes.append(["EnterpriseID", "Address", "Netmask", "Type", "Destination", "Reachable", "Metric", "Preference", "Flags", "C-Tag", "S-Tag", "Handoff", "Mode", "Age"])
        for entry in reply:
            routetbl = entry["routes"]
            for route in routetbl:
				if str(route["type"]) == "edge2edge":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), "N/A", "N/A", str(route["age_s"])])
				elif str(route["type"]) == "datacenter":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), "0", str(-1), str(-1), "N/A", "N/A", str(route["age_s"])])
				else :
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), str(route["handoff"]), str(route["mode"]), str(route["age_s"])])
        pretty_print_table(routes)

class routeE2EPGDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"routes"}
        if values:
            if (len(values) == 2):
                params = {"entr": values[0], "dip": values[1]}
            else:
                params = {"entr": values[0], "dip": "all"}
        else:
            params = {"entr": "all", "dip":"all"}
        reply = remote_server.routeE2EPGDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        routes = []
        routes.append(["EnterpriseID", "Address", "Netmask", "Type", "Destination", "Reachable", "Metric", "Preference", "Flags", "C-Tag", "S-Tag", "Handoff", "Mode", "Age"])
        for entry in reply:
            routetbl = entry["routes"]
            for route in routetbl:
				if str(route["type"]) == "edge2edge":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), "N/A", "N/A", str(route["age_s"])])
				elif str(route["type"]) == "datacenter":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), "0", str(-1), str(-1), "N/A", "N/A", str(route["age_s"])])
				else :
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), str(route["handoff"]), str(route["mode"]), str(route["age_s"])])
        pretty_print_table(routes)

class routeE2EDCDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"routes"}
        if values:
            if (len(values) == 2):
                params = {"entr": values[0], "dip": values[1]}
            else:
                params = {"entr": values[0], "dip": "all"}
        else:
            params = {"entr": "all", "dip":"all"}
        reply = remote_server.routeE2EDCDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        routes = []
        routes.append(["EnterpriseID", "Address", "Netmask", "Type", "Destination", "Reachable", "Metric", "Preference", "Flags", "C-Tag", "S-Tag", "Handoff", "Mode", "Age"])
        for entry in reply:
            routetbl = entry["routes"]
            for route in routetbl:
				if str(route["type"]) == "edge2edge":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), "N/A", "N/A", str(route["age_s"])])
				elif str(route["type"]) == "datacenter":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), "0", str(-1), str(-1), "N/A", "N/A", str(route["age_s"])])
				else :
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), str(route["handoff"]), str(route["mode"]), str(route["age_s"])])
        pretty_print_table(routes)

class routePGDCDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"routes"}
        if values:
            if (len(values) == 2):
                params = {"entr": values[0], "dip": values[1]}
            else:
                params = {"entr": values[0], "dip": "all"}
        else:
            params = {"entr": "all", "dip":"all"}
        reply = remote_server.routePGDCDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        routes = []
        routes.append(["EnterpriseID", "Address", "Netmask", "Type", "Destination", "Reachable", "Metric", "Preference", "Flags", "C-Tag", "S-Tag", "Handoff", "Mode", "Age"])
        for entry in reply:
            routetbl = entry["routes"]
            for route in routetbl:
				if str(route["type"]) == "edge2edge":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), "N/A", "N/A", str(route["age_s"])])
				elif str(route["type"]) == "datacenter":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), "0", str(-1), str(-1), "N/A", "N/A", str(route["age_s"])])
				else :
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), str(route["handoff"]), str(route["mode"]), str(route["age_s"])])
        pretty_print_table(routes)

class routeTesterDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"routes"}
        if values:
            if (len(values) == 2):
                params = {"entr": "all", "dip": values[1]}
            else:
                params = {"entr": values[0], "dip": "all"}
        else:
            params = {"entr": "all", "dip":"all"}
        reply = remote_server.routeTesterDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        routes = []
        routes.append(["EnterpriseID", "Address", "Netmask", "Type", "Destination", "Reachable", "Metric", "Preference", "Flags", "C-Tag", "S-Tag", "Handoff", "Mode", "Age"])
        for entry in reply:
            routetbl = entry["routes"]
            for route in routetbl:
				if str(route["type"]) == "edge2edge":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), "N/A", "N/A", str(route["age_s"])])
				elif str(route["type"]) == "datacenter":
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), "0", str(-1), str(-1), "N/A", "N/A", str(route["age_s"])])
				else :
				    routes.append([str(entry["enterprise_id"]), route["address"], route["netmask"], route["type"], route["destination"], str(route["reachable"]), str(route["metric"]), str(route["preference"]), route["flags"], str(route["c-tag"]), str(route["s-tag"]), str(route["handoff"]), str(route["mode"]), str(route["age_s"])])
        pretty_print_table(routes)

class verboseRouteDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"routes"}
        if values:
            if (len(values) == 2):
                params = {"entr": values[0], "dip": values[1]}
            else:
                params = {"entr": values[0], "dip": "all"}
        else:
            params = {"entr": "all", "dip":"all"}
        reply = remote_server.routeDebugDump(**params) 
        print json.dumps(reply, sort_keys = True, indent = 2)

class RouteSummary(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"rsummary"}
        if values:
            if (len(values) == 2):
                params = {"entr": values[0], "edge": values[1]}
            else:
                params = {"entr": values[0], "edge": "all"}
        else:
            params = {"entr": "all", "edge":"all"}
        reply = remote_server.routeSummary(**params) 
        print json.dumps(reply, sort_keys = True, indent = 2)

def format_app_string(app_id, app_string):
    output = app_string + "(" + str(app_id) + ")"
    return output

class FlowDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values:
            params = {"debug":"flowdump", "val":1, "dip": values }
        else:
            params = {"debug":"flowdump", "val":1, "dip": "all" }
        reply = remote_server.flowDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        output = []
        output.append(["VCE", "LFID", "RFID", "FDSN", "MAX_RECV_FDSN",
                       "FDSN_READ", "LAST_LATE_FDSN", "SRC IP", "DEST IP",
                       "SRC PORT", "DEST PORT", "PROTO", "PRIORITY", "ROUTE-POL", "LINK-POL", "TRAFFIC-TYPE", "FLAGS", "IDLE TIME MS", "PEER RC MS", "PEER INSTANCE ID"])
        for entry in reply:
            flowtbl = entry["flow"]
            for flow in flowtbl:
                output.append([entry["vceid"], str(flow["localFlowId"]), str(flow["remoteFlowId"]),
                               str(flow["fdsn"]), str(flow["max_recv_fdsn"]),
                               str(flow["fdsn_read"]), str(flow["last_late_fdsn"]),
                               flow["srcIP"], flow["destIP"], str(flow["srcPort"]),
                               str(flow["destPort"]), str(flow["proto"]), flow["priority"],
                               flow["route"], flow["link"], flow["type"], str(hex(flow["flags1"])),
                               str(flow["idleTimeMs"]), str(flow["peerReconnectTimeMs"]), str(flow["peerInstanceId"])])
        if len(output) > 0:
            pretty_print_table(output)

class StaleFlowDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values:
            params = {"debug": "stale_flow_dump", "val":1, "dip": values}
        else:
            params = {"debug": "stale_flow_dump", "val":1, "dip": "all"}

        output = []
        output.append(["FC_ID", "SIP", "DIP", "SPORT", "DPORT", "DEAD SINCE", "REF OBJS", "RTQ PKTS"])
        reply = remote_server.dumpStaleFlows(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        stale_flows = reply['stale_flows']
        for stale_flow in stale_flows:
            output.append([str(stale_flow['flow_id']), str(stale_flow['sip']), str(stale_flow['dip']),
                           str(stale_flow['sport']), str(stale_flow['dport']), str(stale_flow['dead_since']),
                           str(stale_flow['ref_objs']), str(stale_flow['pkts_in_rt_queue'])])
        if len(output) > 0:
            pretty_print_table(output)

class toggleFlowAgerAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values:
            if len(values) < 1:
                print json.dumps({"result":"not enough arguments"})
            
            arg_val = int(values[0])
            if arg_val != 0 and arg_val != 1:
                print json.dumps({"result":"first argument needs to be 0/1"})
                return

            params = {"enabled": arg_val}
            for i in range(1,len(values)):
                if 'timer_interval_secs' in values[i]:
                    arg_val = values[i].split('=')[1]
                    params.update({'timer_interval_secs': int(arg_val)})
                elif 'idle_timeout_secs' in values[i]:
                    arg_val = values[i].split('=')[1]
                    params.update({'idle_timeout_secs': int(arg_val)})
            
            reply = remote_server.toggleFlowAger(**params)
            print json.dumps(reply)
        else:
            print json.dumps({"result":"no input given"})

class StaleTdDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug": "stale_td_dump"}
        reply = remote_server.dumpStaleTds(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        output = []
        output.append(["TD", "PI", "PEER IP", "PEER TYPE", "VERSION", "STATE", "OBJ STATE", "PHY INTF NAME", "REFCNT", "REF OBJS"])
        stale_tds = reply['stale_tds']
        for stale_td in stale_tds:
            output.append([str(stale_td["td"]), str(stale_td["pi"]), str(stale_td["peer_ip"]), str(stale_td["peer_type"]),
                           str(stale_td["version"]), str(stale_td["state"]), str(stale_td["obj_state"]),
                           str(stale_td["phy_intf_name"]), str(stale_td["ref_cnt"]), str(stale_td["ref_objs"])])
        if len(output) > 0:
            pretty_print_table(output)

class StalePiDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug": "stale_pi_dump"}
        reply = remote_server.dumpStalePi(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        output = []
        output.append(["PI", "PEER LOGICAL ID", "PEER TYPE", "OBJ STATE", "REFCNT", "REF OBJS"])
        stale_pis = reply['stale_pi']
        for stale_pi in stale_pis:
            output.append([str(stale_pi["pi"]), str(stale_pi["peer_logical_id"]), str(stale_pi["peer_type"]),
                           str(stale_pi["obj_state"]), str(stale_pi["ref_cnt"]), str(stale_pi["ref_objs"])])
        if len(output) > 0:
            pretty_print_table(output)

class PacketLeakCheck(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if len(values) < 1:
            print "Insufficinet Arguments, Valid arguments are ON/OFF/DUMP"
            return

        params = {"debug": "pkt_leak_dump", "arg": values[0]}
        reply = remote_server.pktDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        if values[0] == "dump":
            output = []
            output.append(["PKT", "PI", "Tracker", "Last-path", "Flags"])
            pkts = reply['leak_pkt']
            for pkt in pkts:
                output.append([str(pkt['pkt']), str(pkt['pi']), str(pkt['path']), str(pkt['last-path']), str(pkt['flags'])])

            if len(output) > 0:
                pretty_print_table(output)
        else:
            print json.dumps(reply, sort_keys = True, indent = 2)

        return

class PacketTracker(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if len(values) < 6:
            print "Insufficinet Arguments"
            return

        params = {"debug": "pkt_track", "sip": values[0], "sport": values[1], "dip": values[2], "dport": values[3], "proto": values[4], "count":values[5]}
        reply = remote_server.pktTrace(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

        return

class reloadConfigs(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug": "reload_configs"}
        reply = remote_server.reloadConfigs(**params)

class JitterDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values:
            params = {"debug":"flowdump", "val":2, "dip": values }
        else:
            params = {"debug":"flowdump", "val":2, "dip": "all" }
        reply = remote_server.flowDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        output = []
        output.append(["GWIP", "FDSN", "FDSN_READ", "LAST_LATE_FDSN", "DEP_INTERVAL",
                       "JBUF_ENQUEUE", "JBUF_DEQUEUE", "JBUF_TDEQUEUE", "SRC IP", "DEST IP",
                       "SRC PORT", "DEST PORT", "PROTO"])
        for entry in reply:
            flowtbl = entry["flow"]
            for flow in flowtbl:
                output.append([entry["vceid"], str(flow["fdsn"]), str(flow["fdsn_read"]),
                               str(flow["last_late_fdsn"]), str(flow["depInterval"]), str(flow["jbufEnqueueCnt"]),
                               str(flow["jbufDequeueCnt"]), str(flow["jbufRealDequeueCnt"]), flow["srcIP"], flow["destIP"],
                               str(flow["srcPort"]), str(flow["destPort"]), str(flow["proto"])])
        pretty_print_table(output)
                

class FlowFlushAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"flowflush"}
        reply = remote_server.flowDebugFlush(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class ikeDeleteAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"cookie":values[0]}
        reply = remote_server.ikeDebugDeleteSpd(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class verboseIkeDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"ike"}
        reply = remote_server.ikeDebugDump(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)
        
class datacenterVpnStatusAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"ike"}
        reply = remote_server.datacenterVpnStatusDump(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)
        
class ikeDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"ike"}
        reply = remote_server.ikeDebugDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        #first print the velocloud tunnels
        vpn_edge_to_edge = []
        vpn_edge_to_edge_cnt = 0
        vpn_edge_to_edge.append(["Name", "Source", "Destination", "Instance ID", "Cookie", "TD version", "State"])
        for entry in reply["descriptors"]:
            if (entry["type"] == "Velocloud"):
                vpn_edge_to_edge_cnt += 1
                state = "DOWN"
                if (entry["up"] == 1):
                    state = "UP"
                vpn_edge_to_edge.append([entry["name"], entry["source"], entry["dest"], str(entry["inst_id"]), str(entry["cookie"]), entry["td_version"], state])
        if (vpn_edge_to_edge_cnt > 0):
            print "VeloCloud Edge Tunnels"
            print "============================================================================="
            pretty_print_table(vpn_edge_to_edge)
        print ""
        #now the DC VTI tunnels
        vpn_vti = []
        vpn_vti_cnt = 0
        vpn_vti.append(["Name", "Source", "Destination", "Instance ID", "Cookie", "Type", "Local VTI IP", "Peer VTI IP", "State"])
        for entry in reply["descriptors"]:
            if ((entry["type"] != "Velocloud") and (entry["type"] != "Cisco ASA") and (entry["type"] != "Generic Policy")):
                vpn_vti_cnt += 1
                vpn_vti.append([entry["name"], entry["source"], entry["dest"], str(entry["inst_id"]), str(entry["cookie"]), entry["type"],
                                entry["local_vti_ip"], entry["peer_vti_ip"], entry["state"]])
        if (vpn_vti_cnt > 0):
            print "Datacenter VTI Tunnels"
            print "=============================================================================================================="
            pretty_print_table(vpn_vti)
        print ""
        #now the DC ASA tunnels
        vpn_asa = []
        vpn_asa_cnt = 0
        vpn_asa.append(["Name", "Source", "Destination", "Instance ID", "Cookie", "Type", "State"])
        for entry in reply["descriptors"]:
            if ((entry["type"] == "Cisco ASA") or (entry["type"] == "Generic Policy")):
                vpn_asa_cnt += 1
                vpn_asa.append([entry["name"], entry["source"], entry["dest"], str(entry["inst_id"]), str(entry["cookie"]), entry["type"], entry["state"]])
        if (vpn_asa_cnt > 0):
            print "Datacenter ASA/Policy Based Tunnels"
            print "==========================================================="
            pretty_print_table(vpn_asa)

class routeInitReqAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"edge_id":values[0]}
        reply = remote_server.routeInitReq(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class routeTestReqAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"edge_id":values[0], "subnets":int(values[1])}
        reply = remote_server.routeTestReq(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class ikeDownAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"cookie":values[0]}
        reply = remote_server.ikeDebugDown(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class ikeDeleteP1SaAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"peerIp":values[0], "cookie":values[1]}
        reply = remote_server.ikeDebugDeleteP1Sa(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class vpnStateUpdateAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"cookie":values[0]}
        reply = remote_server.vpnStateUpdate(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class ikeSetDebugLevelAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"level":int(values[0])}
        reply = remote_server.ikeSetDebugLevel(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class ikeStartDebugAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"cookie":values[0]}
        reply = remote_server.ikeStartDebug(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class ikeSetDynamicLogAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"level":int(values[0])}
        reply = remote_server.ikeSetDynamicLog(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class ikeChildsaDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"ike_childsa"}
        reply = remote_server.ikeChildsaDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        #first print the Security Policy
        ike_childsa = []
        ike_childsa.append(["Index", "Cookie", "SpdId", "IkeSaId", "Flags", "Dir",
                            "Spi", "Usage", "PeerPort", 
                            "Auth", "Encr", "Tunnel // Traffic"])
        for entry in reply["descriptors"]:
            ike_childsa.append([entry["index"], entry["cookie"], entry["SpdId"], entry["IkeSaId"],
                                entry["saFlags"], entry["dir"],
                                entry["SaSpi"], entry["usage"],
                                entry["SaUdpEncPort"],
                                entry["auth_algs"], entry["encr_algs"], entry["tunnel_traffic"]])

        print "Child SA"
        print "================================================================================""================================================================================""=============================="
        pretty_print_table(ike_childsa)

class ikeSaDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"ike_sa"}
        reply = remote_server.ikeSaDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        #first print the Security Policy
        ike_sa = []
        ike_sa.append(["Index", "IkeSaId", "Cookie", "IKE", "Flags", "Dir", "NAT",
                       "Ike Spi/Cookie", "PeerAddr", "State", "Usage"])
        for entry in reply["descriptors"]:
            ike_sa.append([entry["index"], entry["Ikeid"], entry["cookie"],
                           entry["ike_version"], entry["flags"], entry["dir"],
                           entry["nat"], entry["SaSpi"], entry["peer_addr"],
                           entry["state"], entry["usage"]])

        print "IKE SA"
        print "================================================================================""======================================================================"
        pretty_print_table(ike_sa)

class ikeSpdDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"ike_spd"}
        reply = remote_server.ikeSpdDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        #first print the Security Policy
        ike_spd = []
        ike_spd.append(["Index", "SpdId", "Cookie", "Flags", "Mode",
                        "SecuProto", "Auth", "Encr", "Tunnel", "Traffic"])
        for entry in reply["descriptors"]:
            ike_spd.append([entry["pxSp_index"], entry["SpdId"], entry["cookie"],
                            entry["pxSp_flags"], entry["SaMode"],
                            entry["SecuProto"], entry["auth_algs"], entry["encr_algs"],
                            entry["tunnel"], entry["traffic"]])

        print "Security Policy"
        print "================================================================================""======================================================================"
        pretty_print_table(ike_spd)

class dynbwDbgDump(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"dynbwdbg"}
        reply = remote_server.dynbwDbgDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        dynbwdbg = []
        dynbwdbg.append(["debug", "noabort", "disable", "window",
                         "min_pkts", "bwdecr_time", "bwincr_time",
                         "bwincr_maxtime", "wait_bwtest", "rate_tlrnc",
                         "max_diff", "force_max", "force_cnt", 
                         "drop_delay", "drop_delay_cnt", "stop_decr",
                         "wired_nodynbw", "min_latency", "latency_tlrnc",
                         "pp_test", "slow_int", "fast_int", "slow_pkts", "fast_pkts"])
        dynbwdbg.append([str(reply["debug"]), str(reply["noabort"]),
                        str(reply["disable"]), str(reply["window"]),
                        str(reply["min_pkts"]), str(reply["bwdecr_time"]),
                        str(reply["bwincr_time"]), str(reply["bwincr_maxtime"]),
                        str(reply["wait_bwtest"]), str(reply["rate_tlrnc"]),
                        str(reply["max_diff"]), str(reply["force_max"]),
                        str(reply["force_cnt"]), 
                        str(reply["drops_delay"]), str(reply["drops_delay_cnt"]),
                        str(reply["stop_decr"]), str(reply["wired_nodynbw"]),
                        str(reply["min_latency"]), str(reply["latency_tlrnc"]),
                        str(reply["pp_test"]), str(reply["slow_int"]), str(reply["fast_int"]),
                        str(reply["slow_pkts"]), str(reply["fast_pkts"])])
        pretty_print_table(dynbwdbg)

class hfscDbgDump(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"hfscdbg", "sched": values[0], "specific": values[1], "detail": int(values[2])}
        reply = remote_server.hfscDbgDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        hfscdbg = []
        hfscdbg.append(["name", "parent", "children", "qlen",
                        "drops", "packets", "bytes"])
        if int(values[2]) == 0:
            for entry in reply["hfsc"]:
                hfscdbg.append([str(entry["name"]), str(entry["parent"]),
                                str(entry["children"]), str(entry["qlen"]),
                                str(entry["drops"]), str(entry["packets"]),
                                str(entry["bytes"])])
            pretty_print_table(hfscdbg)
        else:
            # Hard to format the detailed response, dump json, analyze offline
            json.dump(reply, sys.stdout)

class handoffqDbgDump(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"handoffqdbg"}
        reply = remote_server.handoffqDbgDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        handoffqdbg = []
        handoffqdbg.append(["name", "qlimit", "lockfree", "sleeping",
                            "wokenup", "enq", "deq", "drops", "head",                            "tail", "dummy", "next", "state"])
        for entry in reply["handoffq"]:            handoffqdbg.append([str(entry["name"]), str(entry["qlimit"]),
                                str(entry["lockfree"]), str(entry["sleeping"]),
                                str(entry["wokenup"]), str(entry["enq"]),
                                str(entry["deq"]), str(entry["drops"]),
                                hex(entry["head"]), hex(entry["tail"]),
                                hex(entry["dummy"]), hex(entry["next"]),
                                str(entry["state"])])
        pretty_print_table(handoffqdbg)

class PktsQedDbgDump(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"pktsqeddbg"}
        reply = remote_server.PktsQedDbgDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        pktsqeddbg = []
        pktsqeddbg.append(["name", "packets"])
        for entry in reply["pktsqed"]:
            pktsqeddbg.append([entry["name"], str(entry["queued"])])
        pretty_print_table(pktsqeddbg)

class linkBwCapDump(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"bwcap"}
        reply = remote_server.linkBwCapDump(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        linkbw = []
        linkbw.append(["VCEID", "CurCap", "OrigCap", "wstart", 
                       "decr", "incr", "test", "force",
                       "Nforced", "pkts", "nacks",
                       "rxkbps", "txkbps", "abort", "init", "netcap",
                       "delta", "minlat", "avglat"])
        for entry in reply["bwcap"]:
            linkbw.append([entry["vceid"], str(entry["bwcap"]),
                           str(entry["msrcap"]),
                           str(entry["wstart"]), 
                           str(entry["decr"]), str(entry["incr"]),
                           str(entry["test"]), str(entry["force"]),
                           str(entry["Nforced"]), str(entry["pkts"]),
                           str(entry["nacks"]), str(entry["rxbps"]),
                           str(entry["txbps"]),
                           str(entry["abort"]), str(entry["init"]),
                           str(entry["netcap"]), str(entry["delta"]),
                           str(entry["minlat"]), str(entry["avglat"])])
        pretty_print_table(linkbw)

class loggerSetSquelchState(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        log_squelch_state = -1
        log_squelch_max = -1
        for i in range (len(values)):
            if  values[i].startswith("max="):
                log_squelch_max = int(values[i].split("=")[1])
            elif values[i] == "on":
                log_squelch_state = 1
            elif values[i] == "off":
                log_squelch_state = 0
        if (log_squelch_state == -1):
            print "invalid log squelching stat: ", log_level
            return 0
        params = {"state":log_squelch_state, "max":log_squelch_max}
        reply = remote_server.loggerSetSquelchState(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class loggerOverrideDefaultsAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        log_level = -1
        log_modules = ""
        logX = 0
        for i in range (len(values)):
            if values[i] == "logX":
                logX = 1
            elif  values[i].startswith("module="):
                log_modules = values[i].split("=")[1].split(",")
                log_modules = [x.strip().upper() for x in log_modules]
                log_modules = ",".join(log_modules)
            elif values[i].isdigit():
                log_level = int(values[i])
        # if  log_level >= 0 and < max its invalid.
        if not (log_level >= 0  and  log_level <= 8):
            print "invalid log level : ", log_level
            return 0
        # modules should be with in our defined modules range.
        params = {"level":log_level, "module":log_modules, "logX":logX}
        reply = remote_server.loggerOverrideDefaults(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class blockedSubnetDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"blocked_subnets"}
        reply = remote_server.blockedSubnetDump(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class dceDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"dce"}
        reply = remote_server.dceTableDebugDump(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class loggerCtxOnOff(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        log_name = ""
        log_enable = ""
        for i in range (len(values)):
            if  values[i].startswith("name="):
                log_name = values[i].split("=")[1]
            elif values[i].startswith("enable="):
                log_enable = values[i].split("=")[1]
        if not log_name or not log_enable:
                return -1
        params = {"name":log_name, "enable":log_enable}
        reply = remote_server.loggerCtxOnOff(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)
        return 0

class qosNetDebug(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"qos_net", "peer_id": values[0], "action": values[1]}
        reply = remote_server.qosNetDebug(**params)

        if values[1] == "stats":
            qos_stats = []
            qos_stats.append(["Endpoint/Class", "BW Cap (Kbps)", "Weight",
                "Kbps (10s win)", "PPS (10s win)", "Queued pkts", "Queued bytes", "Dropped pkts", "Dropped bytes"])
            for entry1 in reply:
                for entry2 in entry1:
                    qos_stats.append([str(entry2["Peer"]), str(entry2["bw_cap"]),
                        str(format(entry2["weight"], '.2f')), str(entry2["bytes_rate"]),
                        str(entry2["pkts_rate"]), str(entry2["pkts_queued"]),
                        str(entry2["bytes_queued"]), str(entry2["pkts_dropped"]),
                        str(entry2["bytes_dropped"])])
            pretty_print_table(qos_stats)
        elif values[1] == "clear_drops":
            print json.dumps(reply, sort_keys = True, indent = 2)

        return 0

class qosLinkDebug(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"qos_link", "peer_id":values[0], "action": values[1]}
        reply = remote_server.qosLinkDebug(**params)

        if values[1] == "stats":
            link_stats = []
            link_stats.append(["Interface", "Logical-Id", "BW (Kbps)",
                "Kbps (10s win)", "PPS (10s win)", "Queued pkts", "Queued bytes", "Dropped pkts", "Dropped bytes"])
            for entry in reply:
                link_stats.append([entry["ifname"], entry["logical_id"], 
                    str(entry["bw_cap"]), str(entry["bytes_rate"]),
                    str(entry["pkts_rate"]), str(entry["pkts_queued"]),
                    str(entry["bytes_queued"]), str(entry["pkts_dropped"]),
                    str(entry["bytes_dropped"])])
            pretty_print_table(link_stats)
        elif values[1] == "clear_drops":
            print json.dumps(reply, sort_keys = True, indent = 2)

class PlHierDebug(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"pl_hier_dbg", "type":values[0], "action":values[1]}
        reply = remote_server.PlHierDebug(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)
        return 0

class enableLatProbe(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug" : "enable_lat_probe", "logical_id" : values[0], "probe_dest" : values[1], "probe_intvl" :
            values[2], "dump_probe_count" : values[3]}
        reply = remote_server.enableLatProbe(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)
        return 0

        #params = {"debug":"enable_lat_probe", "logical_id" : values[0]

class disableLatProbe(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug" : "disable_lat_probe", "logical_id" : values[0]}
        reply = remote_server.disableLatProbe(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)
        return 0

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

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        output = []
        output.append(["TYPE", "OSIP", "ODIP", "OSPORT", "ODPORT", "OPROTO", 
				"MSIP", "MDIP", "MSPORT", "MDPORT", "MPROTO", "2TABLES",
				"ENTERPRISE_ID", "VCEID" ])
        for entry in reply:
            orig = entry["Original"]
            mod = entry["Modified"]
	    output.append([ entry["Type"], orig["sip"], orig["dip"], str(orig["sport"]),
			    str(orig["dport"]), str(mod["protocol"]), mod["sip"], mod["dip"],
			    str(mod["sport"]), str(mod["dport"]), str(mod["protocol"]),
			    str(entry["2tables"]), str(entry["enterprise_logical_id"]), str(entry["vce_logical_id"]) ])
	pretty_print_table(output)

class remoteNatAddEntryAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"remote_nat_add", "nat_entries":int(values[0]), "pat_entries":int(values[1])}
        reply = remote_server.remoteNatAdd(**params)
	print json.dumps(reply, sort_keys = True, indent = 2)

class remoteNatFloodEntryAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"remote_nat_flood", "nat_entries":int(values[0]), "sleep":int(values[1]), "nthreads":int(values[2]), "stop":int(values[3])}
        reply = remote_server.remoteNatFlood(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class flowStats(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"flow_stats"}
        params = {"debug" : "flow_stats", "logical_id" : values[0]}
        reply = remote_server.flowStats(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        flow_stats = []
        if (len(reply) > 1):
            flow_stats.append(["Path", "Total Flows", "TCP Flows", "UDP Flows", "ICMP Flows", "Other Flows"])
            for entry in reply:
                flow_stats.append([entry["Path"], str(entry["Total Flows"]), 
                        str(entry["Active TCP Flows"] - entry["Dead TCP Flows"]), 
                        str(entry["Active UDP Flows"] - entry["Dead UDP Flows"]), 
                        str(entry["Active ICMP Flows"] - entry["Dead ICMP Flows"]), 
                        str(entry["Active other Flows"] - entry["Dead other Flows"])])
            pretty_print_table(flow_stats)
        else:
            print json.dumps(reply, sort_keys = True, indent = 2)

class uptime(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"uptime"}
        reply = remote_server.uptime(**params)

        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        elapsed_ms = reply["uptime"]
        m,s = divmod((elapsed_ms/1000),60)
        h,m = divmod(m,60)
        d,h = divmod(h,24)
        print "Uptime: %02d:%02d:%02d, %d days" % (h,m,s,d)
        print "Start: %s, Current: %s" % (str(reply["start"]), str(reply["current"]))

class bgpDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        bgpRunning = subprocess.check_output("vtysh " + "-d bgpd " + "-c \"show running\"", shell=True)
        if len(bgpRunning) > 0:
                print "show running-config"
                print "====================="
                print bgpRunning
        netnsDump = subprocess.check_output("ip " + "netns " + "list", shell=True)
        if (len(netnsDump) > 1):
            netnsList = string.split(netnsDump, '\n')
            for entry in netnsList:
                if (len(entry) > 1):
                    bgpViewDump = subprocess.check_output("vtysh " + "-d bgpd " + "-c \"show ip bgp view " + entry + " \"", shell=True)
                    if len(bgpViewDump) > 0:
                        print "BGP View for entr ID: " + entry
                        print "========================================"
                        print bgpViewDump
                    
                    bgpOutput = subprocess.check_output("vtysh " + "-d bgpd " + "-c \"show ip bgp view " + entry + " summary\"", shell=True)
                    if len(bgpOutput) > 0:
                        print "BGP View summary for entr ID: " + entry
                        print "========================================"
                        print bgpOutput

                    bgpOutput = subprocess.check_output("vtysh " + "-d bgpd " + "-c \"show ip bgp view " + entry + " scan\"", shell=True)
                    if len(bgpOutput) > 0:
                        print "BGP View scan for entr ID: " + entry
                        print "========================================"
                        print bgpOutput

class netnsDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        netnsDump = subprocess.check_output("ip " + "netns " + "list", shell=True)
        if (len(netnsDump) > 1):
                print "Netns dump"
                print "====================="
                print netnsDump
        netnsList = string.split(netnsDump, '\n')
        for entry in netnsList:
            if (len(entry) > 1):
                netnsOutput = subprocess.check_output("ip " + "netns " + "exec " + entry + " ifconfig -a", shell=True)
                if len(netnsOutput) > 0:
                    print "Netns ifconfig for entr ID: " + entry
                    print "========================================"
                    print netnsOutput
                    
                netnsOutput = subprocess.check_output("ip " + "netns " + "exec " + entry + " netstat -an", shell=True)
                if len(netnsOutput) > 0:
                    print "Netns netstat for entr ID: " + entry
                    print "========================================"
                    print netnsOutput
                    
class vcgMode(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"vcg_mode"}
        reply = remote_server.vcgMode(**params) 
        print json.dumps(reply, sort_keys = True, indent = 2)

class vrfDump(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"vrf_dump"}
        reply = remote_server.vrfDump(**params) 
        print json.dumps(reply, sort_keys = True, indent = 2)

class verboseArpDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"arp"}
        reply = remote_server.arpTableDebugDump(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class pkiDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"pki"}
        reply = remote_server.pkiDebugDump(**params)
        if reply is not None:
            reply["pkiSettings"] = pki.get_pki_settings()
        else:
            reply = {}
            reply["pkiSettings"] = pki.get_pki_settings()
        print json.dumps(reply, sort_keys = True, indent = 2)

class dumpPathPortsAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"ports"}
        reply = remote_server.dumpPathPorts(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class icmpMonitorDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"icmp"}
        reply = remote_server.icmpMonitorDump(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class probeFlapEvent(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug" : "probe_flap_event", "flap_threshold" : values[0], "event_window_in_minutes" : values[1]}
        reply = remote_server.probeFlapEventParams(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)
        return 0

class resetProbesCounters(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"icmpResetCounters"}
        reply = remote_server.icmpResetCounters(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class mallocTrim(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"run_malloc_trim"}
        reply = remote_server.mallocTrim(**params)

class mallocStats(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"run_malloc_stats"}
        reply = remote_server.mallocStats(**params)

class memoryDebugDump(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"memory_dump"}
        reply = remote_server.memoryDebugDump(**params)
        print reply

class bgpNeighborSummaryAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"bgpNeighborSummary"}
        reply = remote_server.bgpNeighborSummaryDump(**params)
        bgp_view_summary = []
        bgp_view_summary.append(["enterpriseLogicalId", "neighborIp", "neighborAS", "msgRcvd", "msgSent", "upDownTime", "state", "pfxRcvd"])
        for entry in reply["bgpNeighborSummary"]:
            bgp_view_summary.append([entry["enterpriseLogicalId"], entry["neighborIp"], entry["neighborAS"], entry["msgRcvd"], entry["msgSent"], entry["upDownTime"], entry["state"], entry["pfxRcvd"]])
        pretty_print_table(bgp_view_summary)
        print ""
        print "dispEntries", reply["dispEntries"], "startEntryIdx", reply["startEntryIdx"], "totalEntries", reply["totalEntries"]


class bgpViewDump(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"bgp_view"}
        reply = remote_server.bgpViewDump(**params)
        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        bgp_view = []
        bgp_view.append(["Enterprise", "Address", "Netmask", "Gateway", "Nbr IP", "Nbr ID", "Metric", 
                         "Type", "Intf", "Sync'd", "Advertise", "Inbound", "Age", "Communities"])
        for entry in reply["bgp_view"]:
            bgp_view.append([entry["enterprise"], entry["addr"], entry["netmask"], entry["gateway"], 
                             entry["neighbor_ip"], entry["neighbor_id"], str(entry["metric"]), 
                             str(entry["metric_type"]), entry["intf"], entry["sync'd"], entry["advertise"], 
                             entry["inbound"], str(entry["age_s"]), 
                             str(entry["communities"])])
        pretty_print_table(bgp_view)

class bgpRedisDump(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"bgp_redis_dump"}
        reply = remote_server.bgpRedisDump(**params)
        if namespace.verbose:
            print json.dumps(reply, sort_keys = True, indent = 2)
            return

        bgp_redis_dump = []
        bgp_redis_dump.append(["Enterprise", "Address", "Netmask", "Gateway", "Nbr IP", "Nbr ID", 
                               "Metric", "Type", "Intf", "route_id", "Communities"])
        for entry in reply["bgp_redis_dump"]:
            bgp_redis_dump.append([entry["enterprise"], entry["addr"], entry["netmask"], entry["gateway"],
                                    entry["neighbor_ip"], entry["neighbor_id"], str(entry["metric"]), 
                                   str(entry["metric_type"]), entry["intf"], entry["route_id"], 
                                   str(entry["communities"])])
        pretty_print_table(bgp_redis_dump)
        print "O - Intra Area, IA - Inter Area, OE1 - External 1, OE2 - External 2"

class oneToOneNatDumpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"one_to_one_nat"}
        reply = remote_server.oneToOneNatDump(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class dpdkPortEnable(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"dpdk_port_enable", "intf": values[0]}
        reply = remote_server.dpdkPortEnable(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class dpdkPortDisable(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"dpdk_port_disable", "intf": values[0]}
        reply = remote_server.dpdkPortDisable(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class dpdkBondDump(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"dpdk_bond_dump", "intf": values[0]}
        reply = remote_server.dpdkBondDump(**params)
        ports = []
        ports.append(["PCI", "Port", "Link"])
        for p in reply:
            ports.append([p['name'], str(p['port']), str(p['link'])])
        pretty_print_table(ports)

class dpdkPortsDump(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"dpdk_ports_dump"}
        reply = remote_server.dpdkPortsDump(**params)
        ports = []
        ports.append(["Name", "Port", "ArrayIndex", "Link", "VlanStrip"])
        for p in reply:
            ports.append([p['name'], str(p['port']), str(p['index']), str(p['link']), str(p['strip'])])
        pretty_print_table(ports)

class edgeClusterInfoDump(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"debug":"edge_cluster_info_dump"}
        reply = remote_server.edgeClusterInfoDump(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class enableEdgeClusterOverride(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"logical_id" : values[0], "cpu_pct" : int(values[1]), "mem_pct" : int(values[2]), "tunnel_pct" : int(values[3])}
        reply = remote_server.enableEdgeClusterOverride(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)
        
class disableEdgeClusterOverride(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"logical_id" : values[0]}
        reply = remote_server.disableEdgeClusterOverride(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class memoryLeak(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"MB_to_leak":int(values[0])}
        reply = remote_server.memoryLeak(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class memoryFragment(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        params = {"MB_to_fragment":int(values[0])}
        reply = remote_server.memoryFragment(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

class InbQosAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):

        if len(values) < 1:
            print "Insufficinet Arguments; Valid arguments are 'provider' or 'link'"
            return
        params = {"debug":"inb_qos", "view": values[0]}
        reply = remote_server.inbQos(**params)
        print json.dumps(reply, sort_keys = True, indent = 2)

#sort help in alphabetical order
class HelpSorterClass(argparse.HelpFormatter):
    def add_arguments(self, actions):
        actions = sorted(actions, key=attrgetter('option_strings'))
        super(HelpSorterClass, self).add_arguments(actions)
        
sysparser = argparse.ArgumentParser(description='system settings', add_help=False)
sysparser.add_argument('--timeout', action='store', nargs=1, metavar='TIMEOUT (SECONDS)', help='Override the default timeout of 5 seconds')        
        
parser = argparse.ArgumentParser(formatter_class=HelpSorterClass, description='Debug dump from gwd')
parser.add_argument('--timeout', action='store', nargs=1, metavar='TIMEOUT (SECONDS)', help='Override the default timeout of 5 seconds')
parser.add_argument('-v', '--verbose', action='store_true', help='Output raw JSON instead of formatted display')
parser.add_argument('--flow_dump', action=FlowDumpAction, nargs='?', default="all", metavar=('[all | dest-ip]'), help='dump the current flow table entries')
parser.add_argument('--flow_flush', action=FlowFlushAction, nargs=0, help='flush out the current flow table entries')
parser.add_argument('--jitter', action=JitterDumpAction, nargs='?', default="all", metavar=('[all | dest-ip]'), help='dump the current jitter buffer enabled flow table entries')
parser.add_argument('--link_stats', action=linkStatsDumpAction, nargs=0, help='dump the link stats of connected edges')
parser.add_argument('--list_edges <apiVer>', action=listConEdgesAction, nargs=1, choices=['1', '2', '3'], help='dump the list of connected edges')
parser.add_argument('--path_stats', action=pathStatsDumpAction, nargs=0, help='dump the path stats of connected edges')
parser.add_argument('--peers', action=peerDumpAction, nargs=0, help='dump the current vc peer table')
parser.add_argument('--endpoints', action=endpointDumpAction, nargs=0, help='dump the current vc endpoint table')
parser.add_argument('--routes', action=routeDumpAction, nargs='*', metavar=('[all | entr_id]', '[all | dip]'), help='dump the current vc route table')
parser.add_argument('--none_handoff_routes', action=routeNoneDumpAction, nargs=0, help='dump the none-handoff route table')
parser.add_argument('--e2e_routes', action=routeE2EDumpAction, nargs='*', metavar=('[all | entr_id]', '[all | dip]'), help='dump the e2e route table')
parser.add_argument('--pg_routes', action=routePGDumpAction, nargs='*', metavar=('[all | entr_id]', '[all | dip]'), help='dump the pg route table')
parser.add_argument('--e2dc_routes', action=routeE2DCDumpAction, nargs='*', metavar=('[all | entr_id]', '[all | dip]'), help='dump the e2dc route table')
parser.add_argument('--e2e_pg_routes', action=routeE2EPGDumpAction, nargs='*', metavar=('[all | entr_id]', '[all | dip]'), help='dump the e2e-pg route table')
parser.add_argument('--e2e_dc_routes', action=routeE2EDCDumpAction, nargs='*', metavar=('[all | entr_id]', '[all | dip]'), help='dump the e2e-dc route table')
parser.add_argument('--pg_dc_routes', action=routePGDCDumpAction, nargs='*', metavar=('[all | entr_id]', '[all | dip]'), help='dump the pg-dc route table')
parser.add_argument('--verbose_routes', action=verboseRouteDumpAction, nargs='*', metavar=('[all | entr_id]', '[all | dip]'), help='verbose dump the current vc route table')
parser.add_argument('--rsummary', action=RouteSummary, nargs='*', metavar=('[all | entr_id]', '[all | edge_id]'), help='routes summary')
parser.add_argument('--ike', action=ikeDumpAction, nargs=0, help='dump the current ike descriptors')
parser.add_argument('--verbose_ike', action=verboseIkeDumpAction, nargs=0, help='verbose dump the current ike descriptors')
parser.add_argument('--datacenter_vpn_status', action=datacenterVpnStatusAction, nargs=0, help='dump the current data center VPN status')
parser.add_argument('--route_init_req', action=routeInitReqAction, nargs=1, metavar=('<logical_id>'), help='request route init for a particular edge <edge_id>')
parser.add_argument('--debug_down_ike', action=ikeDownAction, nargs=1, help='set the ike descriptors to down state & restart')
parser.add_argument('--debug_delete_ike_p1_sa', action=ikeDeleteP1SaAction, nargs=2, metavar=('[peer_ip]', '[cookie]'), help='for debugging only - manually delete P1 SA entry')
parser.add_argument('--vpn_state_update', action=vpnStateUpdateAction, nargs=1, help='Update DC VPN state to VCO')
parser.add_argument('--debug_delete_ike_spd', action=ikeDeleteAction, nargs=1, help='for debugging only - manually delete the SPD entry')
parser.add_argument('--ike_setdebuglevel', action=ikeSetDebugLevelAction, nargs=1, help='set ike debug level')
parser.add_argument('--ike_setdynamiclog', action=ikeSetDynamicLogAction, nargs=1, help='set ike dynamic log [0/1]')
parser.add_argument('--ike_childsa', action=ikeChildsaDumpAction, nargs=0, help='dump the current Child SA')
parser.add_argument('--ike_sa', action=ikeSaDumpAction, nargs=0, help='dump the current IKE SA')
parser.add_argument('--ike_spd', action=ikeSpdDumpAction, nargs=0, help='dump the current Security Policy (SP)')
parser.add_argument('--bwcap', action=linkBwCapDump, nargs=0, help='dump the link bandwidth caps')
parser.add_argument('--dynbwdbg', action=dynbwDbgDump, nargs=0, help='dump dynbw related info ')
parser.add_argument('--handoffqdbg', action=handoffqDbgDump, nargs=0, help='dump handoffq related info ')
parser.add_argument('--pktsqed', action=PktsQedDbgDump, nargs=0, help='dump count of packets queued ')
parser.add_argument('--hfscdbg', action=hfscDbgDump, nargs=3, metavar=('[net | link]', '[specifics]', '[detaildump]'),
                    help='[--hfscdbg link none 0] is mostly what you are looking for')
parser.add_argument('--logger_setlevel', action=loggerOverrideDefaultsAction, nargs='+', help='override the default log level of modules. --logger_setlevel level_num [module=moduleName[,moduleName[,...]] [logX]]')
parser.add_argument('--logger_setsquelching', action=loggerSetSquelchState, nargs='+', help='Disable or Enable log squelching, and set maximum number of log entries to be squelched. --logger_setsquelching on|off [max=dddd]')
parser.add_argument('--blocked_subnets', action=blockedSubnetDumpAction, nargs=0, help='dump the current blocked subnets')
parser.add_argument('--logger_on_off', action=loggerCtxOnOff, nargs='+', help='Disable or Enable log using its context name | --logger_on_off name=<ctx name> enable=<on/off>')
parser.add_argument('--nat_dump', action=natDumpAction, nargs=2, metavar=('[all | dest-ip]', '[orig | modified]'), help='Dump NAT info tbl')
parser.add_argument('--nat_add_entry <nat-entries> <pat-entries>', action=remoteNatAddEntryAction, nargs=2, help='Add entries to local and remote NAT/PAT tbl')
parser.add_argument('--nat_flood_entry <nat-entries> <sleep-time> <num-threads>', action=remoteNatFloodEntryAction, nargs=4, help='Add entries to local and remote NAT/PAT tbl in a flood')
parser.add_argument('--dce_list', action=dceDumpAction, nargs=0, help='dump the current Datacenter Edges')
parser.add_argument('--qos_net', action=qosNetDebug, nargs=2, metavar=('[peer_id]', '[stats | clear_drops]'), help='QoS Net Stats')
parser.add_argument('--qos_link', action=qosLinkDebug, nargs=2, metavar=('[peer_id]', '[stats | clear_drops]'), help='QoS Link Stats')
parser.add_argument('--pl_hier_dbg', action=PlHierDebug, nargs=2, metavar=('[qos | link]', '[debug_on | debug_off | dump]'), help='pl_hier_dbg interface')
parser.add_argument('--enable_lat_probe', action=enableLatProbe, nargs=4, metavar=('[logical_id]', '[probe_destination_ip]', '[probe_interval]', '[dump_probes_count]'), help='enable latency probe on edge identified by logical_id. --enable_lat_probe <logical_id> <probe_destination_ip> <probe_interval> <dump_probes_count>')
parser.add_argument('--disable_lat_probe', action=disableLatProbe, nargs=1, metavar=('[logical_id]'), help='Disable latency probe on edge identified by logical_id. --disable_lat_probe <logical_id>')
parser.add_argument('--flow_stats', action=flowStats, nargs=1, metavar=('[logical_id]'), help='Dump path level flow stats for edge identified by logical_id')
parser.add_argument('--uptime', action=uptime, nargs=0, help='Dump process uptime')
parser.add_argument('--vcg_mode', action=vcgMode, nargs=0, help='Display VCG operational mode')
parser.add_argument('--vrf_dump', action=vrfDump, nargs=0, help='Dump configured VRF')
parser.add_argument('--verbose_arp_dump', action=verboseArpDumpAction, nargs=0, help='dump the arp cache for active interfaces')
parser.add_argument('--icmp_monitor', action=icmpMonitorDumpAction, nargs=0, help='dump the ICMP monitor info')
parser.add_argument('--pki', action=pkiDumpAction, nargs=0, help='dump the current pki configuration')
parser.add_argument('--reset_probes_counters', action=resetProbesCounters, nargs=0, help='reset ICMP probes counters')
parser.add_argument('--malloc_trim', action=mallocTrim, nargs=0, help='run malloc_trim')
parser.add_argument('--malloc_stats', action=mallocStats, nargs=0, help='run malloc_stats')
parser.add_argument('--probe_flap_event_config', action=probeFlapEvent, nargs=2, metavar=('[flap_threshold]', '[event_window_in_minutes]'), help='Set probe flap threshold and event window in mins --icmp_probe_flap_event <flap_threshold> <event_window_in_minutes>')
parser.add_argument('--bgpd_dump', action=bgpDumpAction, nargs=0, help='show bgp db status')
parser.add_argument('--netns_dump', action=netnsDumpAction, nargs=0, help='show netns dump')
parser.add_argument('--bgp_view_summary', action=bgpNeighborSummaryAction, nargs=0, help='dump the bgp view summary')
parser.add_argument('--bgp_view', action=bgpViewDump, nargs=0, help='dump the bgp view')
parser.add_argument('--bgp_redis_dump', action=bgpRedisDump, nargs=0, help='dump the bgp redis view')
parser.add_argument('--stale_flow_dump', action=StaleFlowDumpAction, nargs='?', default="all", metavar=('[all | dest-ip]'), help='dump the current stale flow table entries')
parser.add_argument('--flow_ager_toggle', action=toggleFlowAgerAction, nargs='+', metavar=('[enable_or_disable] [timer_iterval_secs] [idle_timeout_secs]'), help='enable/disable flow ager --flow_ager_toggle [1|0:enable/disable] [timer_iterval_secs=<value in seconds] [idle_timeout_secs=<idle timeout in seconds]')
parser.add_argument('--stale_td_dump', action=StaleTdDumpAction, nargs=0, help='Dump the list of stale Tds')
parser.add_argument('--stale_pi_dump', action=StalePiDumpAction, nargs=0, help='Dump the list of stale Pi')
parser.add_argument('--pkt_leak_check', action=PacketLeakCheck, nargs=1, help='Track the leaked packets in the system')
parser.add_argument('--pkt_tracker', action=PacketTracker, nargs=6, help='Track the life cycle of a flow')
parser.add_argument('--reload_configs', action=reloadConfigs, nargs=0, help='reload configs that can be reloaded without requiring edge/gw restart')
parser.add_argument('--dump_path_ports', action=dumpPathPortsAction, nargs=0, help='dump the ports that the gateway has learned for each path')
parser.add_argument('--ike_debug_instance', action=ikeStartDebugAction, nargs=1, help='enable log on a specfic instance')
parser.add_argument('--memory_dump', action=memoryDebugDump, nargs=0, help='Dump the current unknown allocations')
parser.add_argument('--one_to_one_nat', action=oneToOneNatDumpAction, nargs=0, help='dump biz policy 1:1 NAT rules')
parser.add_argument('--dpdk_port_disable', action=dpdkPortDisable, nargs=1, metavar=('[interface physical name]'),
                    help='Disable a dpdk port')
parser.add_argument('--dpdk_port_enable', action=dpdkPortEnable, nargs=1, metavar=('[interface physical name]'),
                    help='Enable a dpdk port')
parser.add_argument('--dpdk_ports_dump', action=dpdkPortsDump, nargs=0, help='Dump dpdk port information')
parser.add_argument('--dpdk_bond_dump', action=dpdkBondDump, nargs=1, metavar=('[interface physical name]'),
                    help='Dump dpdk bond information')
parser.add_argument('--edge_cluster_info_dump', action=edgeClusterInfoDump, nargs=0, help='Dump edge clustering information')
parser.add_argument('--enable_edge_cluster_override', action=enableEdgeClusterOverride, nargs=4, metavar=('[logical_id]', '[cpu_pct]', '[mem_pct]', '[tunnel_pct]'), help='override the stats sent by an edge in the cluster. further stat updates from edge will be ignored until this override is disabled.')
parser.add_argument('--disable_edge_cluster_override', action=disableEdgeClusterOverride, nargs=1, metavar=('[logical_id]'), help='disable override of stats for an edge in a cluster. next update from edge after disable will restore stats to edge-reported values.')
parser.add_argument('--memory_leak', action=memoryLeak, nargs=1, metavar=('[num of MB to leak]'), help='deliberately cause memory to be leaked inside gwd')
parser.add_argument('--memory_fragment', action=memoryFragment, nargs=1, metavar=('[num of MB to fragment]'), help='deliberately cause memory to be fragmented inside gwd')
parser.add_argument('--test_vcrp', action=routeTestReqAction, nargs='*', metavar=('[logical_id]', '[subnets]'), help='Test vcrp routes for a particular edge <edge_id>')
parser.add_argument('--vcrp_tester_routes', action=routeTesterDumpAction, nargs='*', metavar=('[all | entr_id]', '[all | dip]'), help='dump the vcrp tester route table')
parser.add_argument('--inb_qos', action=InbQosAction, nargs=1, help='Update debug log level for inbound QoS messages')

class SYSPARAMS:
    pass

try:
    sysparams = SYSPARAMS()
    sysargs = sysparser.parse_known_args(namespace=sysparams)
    timeout = 5; # timeout (5) to handle bgp_view_summary

    # Timeout: None == default(5), <= 0 means block forever
    if isinstance(sysparams.timeout, list):
        timeout=int(sysparams.timeout[0])

    rpc_client = rpc.get_local_rpc_client(None, 'tcp://127.0.0.1:46464',
                                          log_requests=False, timeout=timeout)
    remote_server = rpc_client.get_proxy()
    
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)

    args = parser.parse_args()
    sys.exit(0)
except rpc.CommunicationError as e:
    print "Server was not listening"
    sys.exit(1)
except RPCError as e:
    print "RPC error: ", e
    sys.exit(1)
