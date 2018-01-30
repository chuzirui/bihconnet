#! /usr/bin/python
#
#   BSD LICENSE
#
#   Copyright(c) 2010-2014 Intel Corporation. All rights reserved.
#   All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions
#   are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#       the documentation and/or other materials provided with the
#       distribution.
#     * Neither the name of Intel Corporation nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#   A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#   OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#   LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#   OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

# VeloCloud NOTE: This file has been extracted (aka cut+paste) from 
# dpdk-2.0.0/tools/dpdk_nic_bind.py and modified to suit velocloud
# requirements. The licence comment above is for the same reason 

import re
import sys, os, getopt, subprocess
import json
import fcntl, socket, struct
import time
from os.path import exists, abspath, dirname, basename

orig_dpdk_cfg={}
rxcore = 1
txcore = 0
packet_size = 4096
packet_pool_size = 131072
default_huge_pagesz = 0
huge_pagesz = 0
huge_page_nr = 0
dpdk_start = False
dpdk_stop = False
dpdk_netrestart = False
gwd_interfaces = []
dpdk_supported_drivers = [
    "e1000", "e1000e", "igb", "ixgbe", "igbvf", "ixgbevf", "i40e", "fm10k", "bonding"]
 
# The PCI device class for ETHERNET devices
ETHERNET_CLASS = "0200"

# global dict ethernet devices present. Dictionary indexed by PCI address.
# Each device within this is itself a dictionary of device properties
devices = {}
# list of supported DPDK drivers
dpdk_drivers = [ "igb_uio" ]

# command-line arg flags
args = []

def usage():
    '''Print usage information for the program'''
    argv0 = basename(sys.argv[0])
    print """
    --start to start dpdk on all the dpdk capable interfaces
    --stop to stop dpdk if we are running in dpdk mode
    """

# This is roughly compatible with check_output function in subprocess module
# which is only available in python 2.7.
def check_output(args, stderr=None):
    '''Run a command and capture its output'''
    return subprocess.Popen(args, stdout=subprocess.PIPE,
                            stderr=stderr).communicate()[0]

def sort_interfaces(interface):
    intf = interface["intf"]
    intf_index = int((re.findall('\d+', intf))[0])
    return intf_index

def has_driver(dev_id):
    '''return true if a device is assigned to a driver. False otherwise'''
    return "Driver_str" in devices[dev_id]

def get_pci_device_details(dev_id):
    '''This function gets additional details for a PCI device'''
    device = {}

    extra_info = check_output(["lspci", "-vmmks", dev_id]).splitlines()

    # parse lspci details
    for line in extra_info:
        if len(line) == 0:
            continue
        name, value = line.split("\t", 1)
        name = name.strip(":") + "_str"
        device[name] = value
    # check for a unix interface name
    sys_path = "/sys/bus/pci/devices/%s/net/" % dev_id
    if exists(sys_path):
        device["Interface"] = ",".join(os.listdir(sys_path))
    else:
        device["Interface"] = ""
    # check if a port is used for ssh connection
    device["Ssh_if"] = False
    device["Active"] = ""

    return device

def get_nic_details():
    '''This function populates the "devices" dictionary. The keys used are
    the pci addresses (domain:bus:slot.func). The values are themselves
    dictionaries - one for each NIC.'''
    global devices
    global dpdk_drivers

    # clear any old data
    devices = {}
    # first loop through and read details for all devices
    # request machine readable format, with numeric IDs
    dev = {};
    dev_lines = check_output(["lspci", "-Dvmmn"]).splitlines()
    for dev_line in dev_lines:
        if (len(dev_line) == 0):
            if dev["Class"] == ETHERNET_CLASS:
                #convert device and vendor ids to numbers, then add to global
                dev["Vendor"] = int(dev["Vendor"],16)
                dev["Device"] = int(dev["Device"],16)
                devices[dev["Slot"]] = dict(dev) # use dict to make copy of dev
        else:
            name, value = dev_line.split("\t", 1)
            dev[name.rstrip(":")] = value

    # check what is the interface if any for an ssh connection if
    # any to this host, so we can mark it later.
    ssh_if = []
    route = check_output(["ip", "-o", "route"])
    # filter out all lines for 169.254 routes
    route = "\n".join(filter(lambda ln: not ln.startswith("169.254"),
                             route.splitlines()))
    rt_info = route.split()
    for i in xrange(len(rt_info) - 1):
        if rt_info[i] == "dev":
            ssh_if.append(rt_info[i+1])

    # based on the basic info, get extended text details
    for d in devices.keys():
        # get additional info and add it to existing data
        devices[d] = dict(devices[d].items() +
                          get_pci_device_details(d).items())

        for _if in ssh_if:
            if _if in devices[d]["Interface"].split(","):
                devices[d]["Ssh_if"] = True
                devices[d]["Active"] = "*Active*"
                break;

        # add igb_uio to list of supporting modules if needed
        if "Module_str" in devices[d]:
            for driver in dpdk_drivers:
                if driver not in devices[d]["Module_str"]:
                    devices[d]["Module_str"] = devices[d]["Module_str"] + ",%s" % driver
        else:
            devices[d]["Module_str"] = ",".join(dpdk_drivers)

        # make sure the driver and module strings do not have any duplicates
        if has_driver(d):
            modules = devices[d]["Module_str"].split(",")
            if devices[d]["Driver_str"] in modules:
                modules.remove(devices[d]["Driver_str"])
                devices[d]["Module_str"] = ",".join(modules)

def dev_id_from_dev_name(dev_name):
    '''Take a device "name" - a string passed in by user to identify a NIC
    device, and determine the device id - i.e. the domain:bus:slot.func - for
    it, which can then be used to index into the devices array'''
    dev = None
    # check if it's already a suitable index
    if dev_name in devices:
        return dev_name
    # check if it's an index just missing the domain part
    elif "0000:" + dev_name in devices:
        return "0000:" + dev_name
    else:
        # check if it's an interface name, e.g. eth1
        for d in devices.keys():
            if dev_name in devices[d]["Interface"].split(","):
                return devices[d]["Slot"]
    # if nothing else matches - error
    print "Unknown device: %s. " \
        "Please specify device in \"bus:slot.func\" format" % dev_name
    sys.exit(1)

def unbind_one(dev_id, force):
    '''Unbind the device identified by "dev_id" from its current driver'''
    dev = devices[dev_id]
    if not has_driver(dev_id):
        print "%s %s %s is not currently managed by any driver\n" % \
            (dev["Slot"], dev["Device_str"], dev["Interface"])
        return

    # prevent us disconnecting ourselves
    if dev["Ssh_if"] and not force:
        print "Routing table indicates that interface %s is active" \
            ". Skipping unbind" % (dev_id)
        return

    # write to /sys to unbind
    filename = "/sys/bus/pci/drivers/%s/unbind" % dev["Driver_str"]
    try:
        f = open(filename, "a")
    except:
        print "Error: unbind failed for %s - Cannot open %s" % (dev_id, filename)
        sys/exit(1)
    f.write(dev_id)
    f.close()

def bind_one(dev_id, driver, force):
    '''Bind the device given by "dev_id" to the driver "driver". If the device
    is already bound to a different driver, it will be unbound first'''
    dev = devices[dev_id]
    saved_driver = None # used to rollback any unbind in case of failure

    # prevent disconnection of our ssh session
    if dev["Ssh_if"] and not force:
        print "Routing table indicates that interface %s is active" \
            ". Not modifying" % (dev_id)
        return

    # unbind any existing drivers we don't want
    if has_driver(dev_id):
        if dev["Driver_str"] == driver:
            print "%s already bound to driver %s, skipping\n" % (dev_id, driver)
            return
        else:
            saved_driver = dev["Driver_str"]
            unbind_one(dev_id, force)
            dev["Driver_str"] = "" # clear driver string

    # if we are binding to one of DPDK drivers, add PCI id's to that driver
    if driver in dpdk_drivers:
        filename = "/sys/bus/pci/drivers/%s/new_id" % driver
        try:
            f = open(filename, "w")
        except:
            print "Error: bind failed for %s - Cannot open %s" % (dev_id, filename)
            return
        try:
            f.write("%04x %04x" % (dev["Vendor"], dev["Device"]))
            f.close()
        except:
            print "Error: bind failed for %s - Cannot write new PCI ID to " \
                "driver %s" % (dev_id, driver)
            return

    # do the bind by writing to /sys
    filename = "/sys/bus/pci/drivers/%s/bind" % driver
    try:
        f = open(filename, "a")
    except:
        print "Error: bind failed for %s - Cannot open %s" % (dev_id, filename)
        if saved_driver is not None: # restore any previous driver
            bind_one(dev_id, saved_driver, force)
        return
    try:
        f.write(dev_id)
        f.close()
    except:
        # for some reason, closing dev_id after adding a new PCI ID to new_id
        # results in IOError. however, if the device was successfully bound,
        # we don't care for any errors and can safely ignore IOError
        tmp = get_pci_device_details(dev_id)
        if "Driver_str" in tmp and tmp["Driver_str"] == driver:
            return
        print "Error: bind failed for %s - Cannot bind to driver %s" % (dev_id, driver)
        if saved_driver is not None: # restore any previous driver
            bind_one(dev_id, saved_driver, force)
        return


def unbind_all(dev_list, force=True):
    """Unbind method, takes a list of device locations"""
    dev_list = map(dev_id_from_dev_name, dev_list)
    for d in dev_list:
        unbind_one(d, force)

def bind_all(dev_list, driver, force=True):
    """Unbind method, takes a list of device locations"""
    global devices

    dev_list = map(dev_id_from_dev_name, dev_list)

    for d in dev_list:
        bind_one(d, driver, force)

    # when binding devices to a generic driver (i.e. one that doesn't have a
    # PCI ID table), some devices that are not bound to any other driver could
    # be bound even if no one has asked them to. hence, we check the list of
    # drivers again, and see if some of the previously-unbound devices were
    # erroneously bound.
    for d in devices.keys():
        # skip devices that were already bound or that we know should be bound
        if "Driver_str" in devices[d] or d in dev_list:
            continue

        # update information about this device
        devices[d] = dict(devices[d].items() +
                          get_pci_device_details(d).items())

        # check if updated information indicates that the device was bound
        if "Driver_str" in devices[d]:
            unbind_one(d, force)

def display_devices(title, dev_list, extra_params = None):
    '''Displays to the user the details of a list of devices given in "dev_list"
    The "extra_params" parameter, if given, should contain a string with
    %()s fields in it for replacement by the named fields in each device's
    dictionary.'''
    strings = [] # this holds the strings to print. We sort before printing
    print "\n%s" % title
    print   "="*len(title)
    if len(dev_list) == 0:
        strings.append("<none>")
    else:
        for dev in dev_list:
            if extra_params is not None:
                strings.append("%s '%s' %s" % (dev["Slot"], \
                                dev["Device_str"], extra_params % dev))
            else:
                strings.append("%s '%s'" % (dev["Slot"], dev["Device_str"]))
    # sort before printing, so that the entries appear in PCI order
    strings.sort()
    print "\n".join(strings) # print one per line

def show_status():
    global devices
    print devices

def parse_args():
    '''Parses the command-line arguments given by the user and takes the
    appropriate action for each'''
    global args
    global dpdk_start
    global dpdk_stop
    global dpdk_netrestart

    if len(sys.argv) <= 1:
        usage()
        sys.exit(0)

    try:
        opts, args = getopt.getopt(sys.argv[1:], "",
                               ["start", "stop", "usage", "netrestart"])
    except getopt.GetoptError, error:
        print str(error)
        print "Run '%s --usage' for further information" % sys.argv[0]
        sys.exit(1)

    for opt, arg in opts:
        if opt == "--help" or opt == "--usage":
            usage()
            sys.exit(0)
        if opt == "--start":
            dpdk_start = True
        if opt == "--stop":
            dpdk_stop = True
        if opt == "--netrestart":
            dpdk_netrestart = True

def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ':'.join(['%02x' % ord(char) for char in info[18:24]])

def parse_etc_configs():
    global gwd_interfaces 
    global default_huge_pagesz
    global huge_pagesz
    global huge_page_nr
    global packet_pool_size
    global packet_size
    global rxcore
    global txcore
    global orig_dpdk_cfg
    global dpdk

    f=open("/etc/config/gatewayd")
    gwd = json.load(f)
    for i in gwd["global"]["wan"]:
        if i not in gwd_interfaces:
            gwd_interfaces.append(i)
    for i in gwd["global"]["vcmp.interfaces"]:
        if i not in gwd_interfaces:
            gwd_interfaces.append(i)
    f.close()

    f=open("/opt/vc/etc/dpdk.json")
    dpdk = json.load(f)
    orig_dpdk_cfg = dpdk
    default_huge_pagesz = dpdk["default_hugepgsz"]
    huge_pagesz = dpdk["huge_pagesz"]
    huge_page_nr = dpdk["huge_page_nr"]
    packet_pool_size = dpdk["packet_pool_size"]
    packet_size = dpdk["skb_data_size"]
    rxcore = dpdk["rxcore"]
    txcore = dpdk["txcore"]
    f.close()

def get_old_gw(dpdk, interface):
    gw = "None"
    if not "interfaces" in dpdk:
        return gw
    sorted_interfaces = sorted(dpdk["interfaces"], key=sort_interfaces)
    for intf in sorted_interfaces:
        if intf["intf"] == interface:
            gw = intf["gw"]        
    return gw

# The list of "status" text strings and what they means are as below
# 
# 1. Unsupported_Driver: One of the interfaces that we want DPDK to run on
#    does not support DPDK
#
# 2. Missing_Interface: The interface we want dpdk to run on is not even
#    showing up in lspci ! Maybe its some virtual vlanX interface ?
#
# 3. No_Management_Interface: The gateway should have at least one non-DPDK
#    interface if we are to run DPDK on the gateway. If it does not have any
#    non-DPDK (ie management) interfaces, then we report this as status and 
#    disallow DPDK
#
# 4. Bad_Num_Cores_<ncores>: Number of CPU cores not upto our expectation
#
# 5. Bad_HUGEPAGE_Config: We need hugepages setup in /etc/default/grub on
#    the Ubuntu machine. And the number of hugepages needs to meet the requirement
#    mentioned in the dpdk.json file
#
# 6. Disabled: Just means that dpdk is not turned on yet
#
# 7. Supported: Means that dpdk is turned on and functional
#
# 8. Unsupported_config: The bond configuration only runs in active-backup mode
#    only.  All other bond modes are not supported.
#
# Note: If gatewayd finds that the status is anything other than Disabled, it will
# NOT try enabling dpdk. So for some reason while manually playing around with things
# like loading unloading drivers etc.., the dpdk.json file ends up with a status other
# than Disabled (say No_Management_Interface for example), then restarting gwd will
# not re-enable dpdk, it will just continue in non-dpdk mode. So to re-enable dpdk,
# we will have to hand-edit the json file and set the status to Disabled and then
# correct whatever was the problem (say add a new management interface) and then
# restart gwd
def write_opt_vc_etc_dpdk():
    global devices
    global gwd_interfaces
    global default_huge_pagesz
    global huge_pagesz
    global huge_page_nr
    global packet_pool_size
    global packet_size
    global rxcore
    global txcore
    global orig_dpdk_cfg
    global ports

    ports = []
    dpdk_capable = []
    unsupported = False
    # This string is parsed inside gwd to see whether the gateway can
    # support dpdk or not. So make sure that if this string is changed
    # here, we change the corresponding check inside gwd also
    if devices:
        unsup_reason = "Supported"
    else:
        # Xen servers for example doesnt have a single PCI device ! so
        # for them start with Disabled rather than Supported
        unsup_reason = "Disabled"
    for pci in devices:
        # This is not the interface we are interested in, continue
        if devices[pci]["Interface"] not in gwd_interfaces:
            continue
        intf = devices[pci]["Interface"]
        driver = devices[pci]["Driver_str"]
        mac = getHwAddr(intf)
        # We need a device thats supported by Intel DPDK, unless all
        # the interfaces of interest are supported by DPDK, we dont 
        # start DPDK on gateway
        if driver not in dpdk_supported_drivers:
            unsupported = True
            unsup_reason = "Unsupported_Driver"
        else:
            ip = "0.0.0.0"
            mask = "0.0.0.0"
            mtu = 0
            try:
                ip = get_ip_address(intf)
                mask = get_ip_netmask(intf)
                mtu = get_mtu(intf)
            except:
                pass
            (gw, metric) = get_ip_gateway_and_metric(intf)
            if not gw:
                gw = get_old_gw(orig_dpdk_cfg, intf)
            static_ip = 1
            if orig_dpdk_cfg["static_ip"]:
                static_ip = 1
            dpdk_capable.append({"intf": intf, "pci": pci, "driver": driver,
                                 "mac": mac, "ip": ip, "mask": mask, "gw": gw,
                                 "metric": metric, "mtu": mtu, "static_ip": static_ip})

    # If for example we are using some bonding driver and the vcmp interface
    # of interest is say "vlan2", that will not show up in the list of
    # dpdk capable interfaces that we parsed above. So declare that we
    # cant support DPDK on this gateway. Gateway we are keeping it strict
    # at the moment - all the interfaces that gateway needs (at most two today
    # on partner gateway) should be dpdk capable or else we wont allow the support.
    # Edge is more relaxed, edge just allows dpdk on whatever interface is capable
    # of dpdk and works in socket mode on other interfaces
    dpdk_intfcs = []
    for d in dpdk_capable:
        dpdk_intfcs.append(d['intf'])

    if not unsupported and (not (set(gwd_interfaces) <= set(dpdk_intfcs))):
        for intf in gwd_interfaces:
            m = re.search("bond", intf)
            if m:
                ip = "0.0.0.0"
                mask = "0.0.0.0"
                mtu = 0
                mac = "0"
                try:
                    ip = get_ip_address(str(intf))
                    mask = get_ip_netmask(str(intf))
                    mtu = get_mtu(str(intf))
                    mac = getHwAddr(intf)
                except:
                    pass
                (gw, metric) = get_ip_gateway_and_metric(str(intf))
                if not gw:
                    gw = get_old_gw(orig_dpdk_cfg, intf)
                static_ip = 1
                if orig_dpdk_cfg["static_ip"]:
                    static_ip = 1

                bond_dir = "/sys/class/net/%s/"%intf

                try:
                    f=open(bond_dir+"address")
                except:
                    print "Missing_Interface"
                    unsupported = True
                    unsup_reason = "Missing_Interface"
                    break

                mac = f.readline()
                f.close()
                mac = mac.rstrip("\n")

                bond_dir = "/sys/class/net/%s/bonding/"%intf

                try:
                    f=open(bond_dir+"active_slave")
                except:
                    unsupported = True
                    unsup_reason = "Missing_Interface"
                    break

                prim_intf = f.readline()
                f.close()
                prim_intf = prim_intf.strip()

                f=open(bond_dir+"slaves")
                slaves = f.read()
                f.close()
                slaves = slaves.rsplit()
                primary = "None"

                for interface in slaves:
                    if (interface == prim_intf):
                        pci = dev_id_from_dev_name(prim_intf)
                        primary = pci
                    else:
                        pci = dev_id_from_dev_name(interface)
                        interface = interface

                    for d in devices.keys():
                        if pci == devices[d]["Slot"]:
                            driver = devices[d]["Driver_str"];

                    ports.append({"driver": driver, "pci" : pci})
                    ports.sort()

                dpdk_capable.append({"intf": intf,
                        "active_slave": primary,
                        "slaves": ports,
                        "driver": "bonding",
                        "mac": mac, "ip": ip, "mask": mask, "gw": gw,
                        "metric": metric, "mtu": mtu, "static_ip": static_ip})

    # Just to be extra cautios, we dont support DPDK on gateways that have
    # only one interface. If for some reason DPDK screws up access to gateway
    # via that interface, we dont want to brick the gateway. So make sure there
    # is at least one another interface in the routing table which (hopefully)
    # means that there is one other way to get into the gateway
    if not unsupported:
        mgmt_if = []
        route = check_output(["ip", "-o", "route"])
        # filter out all lines for 169.254 routes
        route = "\n".join(filter(lambda ln: not ln.startswith("169.254"),
                                 route.splitlines()))
        rt_info = route.split()
        for i in xrange(len(rt_info) - 1):
            if rt_info[i] == "dev":
                if rt_info[i+1] not in gwd_interfaces:
                    mgmt_if.append(rt_info[i+1])
        #if len(mgmt_if) == 0:
            #unsupported = True
            #unsup_reason = "No_Management_Interface"

    cores = check_output(["grep", "-c", "processor", "/proc/cpuinfo"])
    ncores = int(cores)
    coremask = 0
    if (ncores == 0) or (ncores > 64):
        unsupported = True
        unsup_reason = "Bad_Num_Cores_%d" % ncores
    else:
        coremask = 0
        for i in range(0,ncores):
            coremask |= (1 << i)    
    memchannels = "1"
    portmask = 0
    for i in range(0,len(gwd_interfaces)):
        portmask |= (1 << i)    

    # /etc/default/grub needs a config as below (or with more pages) and then
    # we need to restart the machine for that grub config to take effect ! 
    # The above is for ubuntu (also need a grub-update) after that, openwrt
    # and other version of linux-es might have different types of configs
    # GRUB_CMDLINE_LINUX="default_hugepagesz=2M hugepagesz=2M hugepages=2176"
    # Note that above we have given more hugepages than we need. By default in
    # the json configs we are asking for 2048, but above we have are preallocating
    # 2176. This is because on AWS ubuntu machines I have seen that allocating
    # exactly equal to what we want doesnt work always. Someone else seems to eat
    # up some huge pages and hence gwd doesnt end up getting as much as it wants!
    # And hence we are overallocating. Its a TODO: to find who is eating up from
    # these hugepages and cut down that culprit or else we can never really say
    # if we have pre-allocated enough or not
    hugesup = get_hugepage_cfg(default_huge_pagesz, huge_pagesz, huge_page_nr)
    #if not hugesup:
        #unsupported = True
        #unsup_reason = "Bad_HUGEPAGE_Config"

    f = open("/opt/vc/etc/dpdk.json", "w")
    orig_dpdk_cfg.update({"status": unsup_reason, "interfaces": dpdk_capable,
                          "ncores": ncores, "coremask": coremask, "channels": memchannels,
                          "portmask": portmask
                         })
    json.dump(orig_dpdk_cfg, f, sort_keys=True, indent=4)
    f.close()

def bind_from_opt_vc_etc_dpdk():
    f = open("/opt/vc/etc/dpdk.json")
    dpdk = json.load(f)
    dev_list = []
    sorted_interfaces = sorted(dpdk["interfaces"], key=sort_interfaces)
    for d in sorted_interfaces:
        if (d["driver"] == "bonding"):
            os.system("echo -%s > /sys/class/net/bonding_masters" % d["intf"])
            for e in d["slaves"]:
                dev_list.append(e["pci"])
        else:
            dev_list.append(d["pci"])

    bind_all(dev_list, "igb_uio", True)
    f.close()

def unbind_from_opt_vc_etc_dpdk():
    f = open("/opt/vc/etc/dpdk.json")
    dpdk = json.load(f)
    if (dpdk["status"] != "Supported") and (dpdk["status"] != "Aborted"):
        f.close()
        print "DPDK not enabled yet, so nothing to disable\n"
        return
    non_static = 0
    sorted_interfaces = sorted(dpdk["interfaces"], key=sort_interfaces)
    for d in sorted_interfaces:

        if d["driver"] == "bonding":

            # XXX Fixme: Auto creation of bond interface and setting of mode
            # doesn't seem to work on hotplug interface events.  Investigate
            # this further.  For now, simply make the bond device ahead of
            # the definition in /etc/network/interfaces to work around mode
            # setting problem.

            os.system("echo +%s > /sys/class/net/bonding_masters" % d["intf"])
            os.system("ifconfig %s down" % d["intf"])
            os.system("echo 1 > /sys/class/net/%s/bonding/mode" % d["intf"])

            slaves = d["slaves"]
            for s in slaves:
                bind_one(s["pci"], s["driver"], True)

        else:
            bind_one(d["pci"], d["driver"], True)

        # Ok, now put back all the physical interface configs, in theory
        # this is not needed because the hotplug scripts will end up triggering
        # all these automagically, doing it manually nevertheless
        os.system("ifconfig %s up" % d["intf"])
        #os.system("ifconfig %s hw ether %s" % (d["intf"], d["mac"]))
        if d["static_ip"]:
            os.system("ifconfig %s %s netmask %s" % (d["intf"], d["ip"], d["mask"]))
            if d["gw"] != "None":
                if ("metric" in d) and (d["metric"] != None):
                    os.system("route add default gw %s metric %s %s" % (d["gw"], d["metric"], d["intf"]))
                else:
                    os.system("route add default gw %s %s" % (d["gw"], d["intf"]))
        else:
            non_static = non_static + 1

    if non_static:
        os.system("/etc/init.d/networking restart")
        os.system("sudo service network-manager restart")

    f.close()
    dpdk["status"] = "Disabled"
    dpdk["dpdk_init_count"] = 0
    # Now update the json file to say the new status (disabled)
    f = open("/opt/vc/etc/dpdk.json", "w")
    json.dump(dpdk, f, sort_keys=True, indent=4)
    f.close()

def dpdk_cleanup():
    unbind_from_opt_vc_etc_dpdk()

def get_mtu(ifname):
    mtuinfo = check_output(['ip', 'link', 'show', ifname])
    mtu = re.search('.*mtu ([0-9]+) .*', mtuinfo).groups()[0]
    return int(mtu)

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

def get_ip_netmask(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x891B,  # SIOCGIFNETMASK
        struct.pack('256s', ifname[:15])
    )[20:24])

def get_ip_gateway_and_metric(intf):
    route = "/proc/net/route"
    with open(route) as f:
        for line in f.readlines():
            try:
                iface, dest, gw, flags, _, _, metric, _, _, _, _, =  line.strip().split()
                if dest != '00000000' or not int(flags, 16) & 2 or iface != intf:
                    continue
                gwip = socket.inet_ntoa(struct.pack('<L', int(gw,16)))
                return (gwip, metric)
            except:
                continue
    return (None, None)

def get_hugepage_cfg(default_sz, huge_sz, huge_nr):
    grub = "/etc/default/grub"
    found = False
    defsz = 0
    hugsz = 0
    hugnr = 0
    rehugepg = "GRUB_CMDLINE_LINUX=\".*default_hugepagesz=([0-9]+)M.*hugepagesz=([0-9]+)M.*hugepages=([0-9]+).*\"" 
    with open(grub) as f:
        for line in f.readlines():
            m=re.search(rehugepg, line)       
            if m:
                found = True
                defsz = int(m.group(1))
                hugsz = int(m.group(2))
                hugnr = int(m.group(3))
                break
    if not found:
        return 0
    else:
        if (default_sz > defsz) or (huge_sz > hugsz) or (huge_nr > hugnr):
            return 0

    return 1
 
def dpdk_do_netrestart():        
    f = open("/opt/vc/etc/dpdk.json")
    dpdk = json.load(f)
    if dpdk["status"] != "Supported":
        f.close()
        print "DPDK not enabled yet, so nothing to restart\n"
        return
    initcnt = int(dpdk["dpdk_init_count"])
    if initcnt == 0:
        f.close()
        f = open("/opt/vc/etc/dpdk.json", "w")
        dpdk["dpdk_init_count"] = (initcnt + 1)
        json.dump(dpdk, f, sort_keys=True, indent=4)
        f.close()    
        os.system("/etc/init.d/networking restart")
        os.system("sudo service network-manager restart")
        time.sleep(1)

def main():
    '''program main function'''
    global dpdk_start
    global dpdk_stop
    global dpdk_netrestart

    parse_args()
    get_nic_details()
    if dpdk_start:
        parse_etc_configs()
        unsupported = write_opt_vc_etc_dpdk()
        if not unsupported:
            bind_from_opt_vc_etc_dpdk()
    elif dpdk_stop:
        dpdk_cleanup()
    elif dpdk_netrestart:
        dpdk_do_netrestart()

if __name__ == "__main__":
    main()
