#!/bin/sh

iptables -w -F VCMP_IN_ACL
iptables -w -F VCMP_OUT_ACL
iptables -w -F VCMP_FWD_ACL

iptables -w -P INPUT ACCEPT
iptables -w -t nat -F
iptables -w -t mangle -F
/opt/vc/bin/vc_dpdk.sh stop
/etc/init.d/quagga stop
