#! /usr/bin/python

import re
import sys, os, getopt, subprocess
import json
import fcntl, socket, struct
import time
import pyutil.utils as utils
from os.path import exists, abspath, dirname, basename

name2number = {}
cpuinfo = {}
ncpus = 0
taskparams = {}
leavemealone = 0

# The logic in this file is as follow
# First parse the /opt/vc/etc/taskparams.json file. If there is an entry there
# with a name "leavemealone", we dont modify that file, the script terminates. 
# This is to support cases where someone manually punches in some affinities 
# and doesnt want the script to do any jugglery
#
# Next it parse /proc/cpuinfo and basically forms a map of "physical cpus" 
# to processor number. Multiple "processor" values in /proc/cpuinfo can be 
# mapped to the same physical cpu (hyper threading). Note that a socket and
# a core combination will be a "physical" cpu.
#
# Next, for each entry in taskparams.json, it has an array of "logical" core-ids
# which can be 0 to N or a -1 .. So if there are logical core-ids from 0 to 9, 
# that is an expression of desire that "If I have 10 cores, this is the core 
# where this thread should be placed". A -1 means that "place this thread anywhere"
# in which case we just round robin and place the thread on different cores. The
# coreid is also mentioned as a:b where a is the physical core-id and b is the 
# hyperthread on that core. Hyperthreads are worthless as far as I have seen, so
# most of the default settings are a:0, but feel free to put different values for
# hyperthreads if you find it useful. 
#
# If the logical core-id or the hyperthread number we specify is more than what is
# really available, then we modulo those values with what is actuall available. The
# "cpu_affin" array in the file is what gets filled up by the script, so when we 
# create taskparams.json feel free to fill in any value there.
# 
# Note that for edges, there is no variability - a specific edge always has
# the same number of cores/sockets/hyperthreads etc. So for edges we can actually
# just come up with edge specific taskparams.json and avoid all this jugglery. 
# But for gateways we have no option but to try this because each gateway is 
# a very different machine !
#

def fill_cpuinfo(processor, core, socket):
    global ncpus
    global cpuinfo
    global name2number
    global taskparams
    global leavemealone

    if not processor or not core or not socket:
        print 'Unable to parse cpuinfo\n'
        return

    key = "core%s_socket%s" % (core, socket)
    if key in name2number:
        cpunum = name2number[key]
    else:
        cpunum = ncpus
        name2number[key] = cpunum
        ncpus = ncpus + 1

    if cpunum in cpuinfo:
        cpu = cpuinfo[cpunum]
        cpu.append(processor)
    else:
        cpuinfo.update({cpunum: [processor]})

def parse_cpuinfo():
    global ncpus
    global cpuinfo
    global name2number
    global taskparams
    global leavemealone

    processor = None
    core = None
    socket = None
    f = file('/proc/cpuinfo')
    for line in f.readlines():
        line = line.strip()
        if len(line) == 0:
            fill_cpuinfo(processor, core, socket)
            processor = None
            core = None
            socket = None
            continue
        fields = line.split(":")
        fieldname = fields[0].strip().lower()
        if fieldname == "processor":
            processor = fields[1].strip()
        if fieldname == "core id":
            core = fields[1].strip()
        if fieldname == "physical id":
            socket = fields[1].strip()
    f.close()

def parse_taskparams():
    global ncpus
    global cpuinfo
    global name2number
    global taskparams
    global leavemealone

    f = open('/opt/vc/etc/taskparams.json')
    jsondata = json.load(f)
    jdata = utils.cvt_utf8(json.loads(json.dumps(jsondata)))
    for j in jdata:
        if j['name'] == "leavemealone":
            leavemealone = 1
            return
        taskparams.update({j['name']: j})
    f.close()

def modify_taskparams():
    global ncpus
    global cpuinfo
    global name2number
    global taskparams
    global leavemealone

    anycore = 0
    for k in taskparams:
        corelist = taskparams[k]['core_id']
        th_cnt = taskparams[k]['th_cnt']
        newcpus = []
        for i in range(0,th_cnt):
            m=re.match("([+-]?\d+):(\d+)", corelist[i])
            core = int(m.group(1))
            hyper = int(m.group(2))
            if core == -1:
                core = anycore # Just round robin across cores
                anycore = anycore + 1
            hypthreads = cpuinfo[core%ncpus]
            nhypthreads = len(hypthreads)
            hypthread = hypthreads[hyper%nhypthreads]
            newcpus.append(int(hypthread)+1)
        taskparams[k]['cpu_affin'] = newcpus
        
def dump_taskparams():
    global ncpus
    global cpuinfo
    global name2number
    global taskparams
    global leavemealone

    newtaskparams = []
    for k in taskparams:
        newtaskparams.append(taskparams[k])
     
    os.system('cp /opt/vc/etc/taskparams.json /opt/vc/etc/taskparams.json.orig')
    f = open('/opt/vc/etc/taskparams.json', 'w')
    json.dump(newtaskparams, f, sort_keys=True, indent=4)
    f.close()
   
def dump_cpuparams():
    global ncpus
    global cpuinfo
    global name2number
    global taskparams
    global leavemealone

    f = open('/tmp/core2affinity.json', 'w')
    json.dump(cpuinfo, f, sort_keys=True, indent=4)
    f.close()
    f = open('/tmp/core2name.json', 'w')
    json.dump(name2number, f, sort_keys=True, indent=4)
    f.close()

if __name__ == "__main__":
    parse_cpuinfo()
    dump_cpuparams()
    parse_taskparams()
    if leavemealone:
        print 'OK, enjoy the solitude\n'
        quit()
    modify_taskparams()
    dump_taskparams()
