#!/bin/bash

TCPDUMP=/usr/sbin/tcpdump
INTERFACE=""
dpdk_capable=0
result=1
CMDLINE=()

ctrl_c() {
    if [ "$result" == "0" ];
    then
        1>/dev/null /opt/vc/bin/dpdkdump.py --tcpdump off --intf $INTERFACE
    fi
    exit 0    
}

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT

for var in "$@"
do
    intf=""
    if [[ "$var" == *"any"* ]];
    then
        intf="anyinterface"
    fi
    if [[ "$var" == *"eth"* ]];
    then
        intf=$var
    fi
    if [[ "$var" == *"ge"* ]];
    then
        intf=$var
    fi
    if [[ "$var" == *"internet"* ]];
    then
        intf=$var
    fi
    if [[ "$var" == *"bond"* ]];
    then
        intf=$var
    fi
    if [[ "$var" == *"sfp"* ]];
    then
        intf=$var
    fi
    if [ -n "$intf" ];
    then
        CMDLINE+=("tcpdump")
        INTERFACE=$intf
    else
        CMDLINE+=($var)
    fi
done

grep -q "\"intf\":.*\"$INTERFACE\"" /opt/vc/etc/dpdk.json
dpdk_capable=$?
if [ "$dpdk_capable" == "0" ];
then
    grep -q "\"status\":.*\"Supported\"" /opt/vc/etc/dpdk.json
    result=$?
else
    result=1
fi

if [ "$result" == "0" ];
then
    1>/dev/null /opt/vc/bin/dpdkdump.py --tcpdump on --intf $INTERFACE
    $TCPDUMP "${CMDLINE[@]}"
else
    $TCPDUMP $@
fi

if [ "$result" == "0" ];
then
    /opt/vc/bin/dpdkdump.py --tcpdump off --intf $INTERFACE
fi
 
exit 0
