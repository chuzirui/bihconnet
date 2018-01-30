#!/usr/bin/env sh

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

# VeloCloud NOTE: The APIs in this file are extracted (aka cut+paste)
# from the dpdk-2.0.0/tools/setup.sh file and modified to suit our 
# requirements. Maintaining the BSD licence claim above for the same reason

mode="$1"
#VC_DPDK_LIBS=/opt/vc/lib/dpdk/
VC_DPDK_LIBS=
EAL_PARAMS='-n 4'

dpdk_num_hugepages=1

set_opt_vc_param()
{
    sed -i.bak "s/\"$1\":.*[0-9][0-9]*/\"$1\":$2/g" /opt/vc/etc/dpdk.json
}

# NOTE: Any changes in the math here needs to be updated in the API with the 
# same name in file velocloud.src/ops/vcg/gatewayd-dpdk/files/DEBIAN.
adjust_memory_parameters()
{
    freemem=`free | awk 'FNR == 2 {print $2}'`
    if [ $freemem -lt 3800000 ];
    then
        # < 4Gig mem, dpdk is 1 Gig
        dpdk_num_hugepages=1
        # The other buffer values
        dpdk_locked_buffers=92500
        dpdk_critical_buffers=8000
        dpdk_lockfree_buffers=92500
        packet_pool_size=185000
    elif [ $freemem -lt 32000000 ];
    then
        # >4gig < 32Gig mem, dpdk is 2Gig
        dpdk_num_hugepages=2
        # The other buffer values
        dpdk_locked_buffers=370000
        dpdk_critical_buffers=32000
        dpdk_lockfree_buffers=370000
        packet_pool_size=740000
    else
        # >= 32Gig mem, dpdk is 4Gig
        dpdk_num_hugepages=4
        # The other buffer values
        dpdk_locked_buffers=740000
        dpdk_critical_buffers=64000
        dpdk_lockfree_buffers=740000
        packet_pool_size=1480000
    fi

    set_opt_vc_param "huge_page_nr" $dpdk_num_hugepages
    set_opt_vc_param "dpdk_locked_buffers" $dpdk_locked_buffers
    set_opt_vc_param "dpdk_critical_buffers" $dpdk_critical_buffers
    set_opt_vc_param "dpdk_lockfree_buffers" $dpdk_lockfree_buffers
    set_opt_vc_param "packet_pool_size" $packet_pool_size
}

create_mnt_huge()
{
        echo "Creating /mnt/huge and mounting as hugetlbfs"
        mkdir -p /mnt/huge

        grep -s '/mnt/huge' /proc/mounts > /dev/null
        if [ $? -ne 0 ] ; then
                mount -t hugetlbfs nodev /mnt/huge
        fi
}

#
# Removes hugepage filesystem.
#
remove_mnt_huge()
{
        echo "Unmounting /mnt/huge and removing directory"
        grep -s '/mnt/huge' /proc/mounts > /dev/null
        if [ $? -eq 0 ] ; then
                umount /mnt/huge
        fi

        if [ -d /mnt/huge ] ; then
                rm -R /mnt/huge
        fi
}

#
# Creates hugepages.
# 
# NOTE: On gateway we DO NOT do this since we expect this to be done via GRUB
#
set_non_numa_pages()
{
        cur_pages=`sysctl vm.nr_hugepages | sed -rn 's/^.*vm.nr_hugepages = ([0-9]+)/\1/p'`
        echo "Reserving hugepages $cur_pages, $dpdk_num_hugepages"
        sysctl -w vm.nr_hugepages=$dpdk_num_hugepages
}

#
# Start in disabled state on bootup
#
start_with_dpdk_disabled()
{
        sed -r -i.bak "s/(.*)\"status\".*:.*\".*\"(.*)/\1\"status\":\"Disabled\"\2/g" /opt/vc/etc/dpdk.json
        sed -r -i.bak "s/(.*)\"dpdk_init_count\".*:.*[0-9][0-9]*(.*)/\1\"dpdk_init_count\":0\2/g" /opt/vc/etc/dpdk.json
        sync
        exit
}

#
# Module load error
#
record_module_load_error()
{
        sed -i.bak "s/\"status\":.*\".*\"/\"status\":\"Kernel_Module_Load_Error\"/g" /opt/vc/etc/dpdk.json 
        sync
        exit
}

#
# Unloads igb_uio.ko.
#
remove_igb_uio_module()
{
        echo "Unloading any existing DPDK UIO module"
        /sbin/lsmod | grep -s igb_uio > /dev/null
        if [ $? -eq 0 ] ; then
                /sbin/rmmod igb_uio
        fi
}

#
# Loads new igb_uio.ko (and uio module if needed).
#
load_igb_uio_module()
{
        /sbin/lsmod | grep -s uio > /dev/null
        if [ $? -ne 0 ] ; then
                modinfo uio > /dev/null
                if [ $? -eq 0 ]; then
                        echo "Loading uio module"
                        /sbin/modprobe uio
                fi
        fi

        # UIO may be compiled into kernel, so it may not be an error if it can't
        # be loaded.

        echo "Loading DPDK UIO module"
        /sbin/lsmod | grep -s igb_uio > /dev/null
        if [ $? -ne 0 ] ; then
                modinfo igb_uio > /dev/null
                if [ $? -eq 0 ]; then
                        echo "Loading igb_uio module"
                        /sbin/modprobe igb_uio
                        if [ $? -ne 0 ]; then
                                record_module_load_error
                        fi
                else
                        record_module_load_error
                fi
        fi
}

#
# Unloads the rte_kni.ko module.
#
remove_kni_module()
{
        echo "Unloading any existing DPDK KNI module"
        /sbin/lsmod | grep -s rte_kni > /dev/null
        if [ $? -eq 0 ] ; then
                /sbin/rmmod rte_kni
        fi
}

#
# Loads the rte_kni.ko module.
#
load_kni_module()
{
    echo "Loading DPDK UIO module"
    /sbin/lsmod | grep -s rte_kni > /dev/null
    if [ $? -ne 0 ] ; then
            modinfo rte_kni > /dev/null
            if [ $? -eq 0 ]; then
                    echo "Loading rte_kni module"
                    /sbin/modprobe rte_kni
                    if [ $? -ne 0 ]; then
                            record_module_load_error
                    fi
            else
                    record_module_load_error
            fi
    fi
}

case "$mode" in

bootup)
    start_with_dpdk_disabled
    ;;

start)
    load_igb_uio_module
    load_kni_module
    adjust_memory_parameters
    #set_non_numa_pages
    create_mnt_huge
    /opt/vc/bin/vc_dpdk.py --start
    ;;

stop)

    # NOTE: The KNI module has to be removed first, because that frees up
    # the ethN interface name that the KNI was using to be bound to the real
    # in-kernel driver. Otherwise the in-kernel driver will end up picking
    # a different ethY interface name, we dont want interface names to be
    # changing across dpdk/non-dpdk modes
    remove_kni_module

    # First stop the igb_uio, then remove the huge pages
    /opt/vc/bin/vc_dpdk.py --stop

    remove_mnt_huge
    remove_igb_uio_module
    start_with_dpdk_disabled
    ;;

netrestart)
    /opt/vc/bin/vc_dpdk.py --netrestart
    ;;

abort)
    sed -i.bak "s/\"status\".*:.*\".*\"/\"status\":\"Aborted\"/g" /opt/vc/etc/dpdk.json
    ;;

disable)
    set_opt_vc_param "dpdk_enabled" 0
    set_opt_vc_param "dpdk_use_bufpool_only" 0
    ;;

routeadd)
    GW=$(/sbin/ip route | awk '/default/ { print $3 }')
    if echo "$GW" | grep -q "$2"; 
    then
        exit 0
    fi
    route add default gw $2 metric $3 $4
    ;;

*) echo "Invalid command: $mode"

esac

