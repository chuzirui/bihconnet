#!/bin/sh

CONF="/etc/config/gatewayd-tunnel"
GWD_CONF="/etc/config/gatewayd"

. $CONF

EC2METADATA_SRC=" -s 169.254.169.254/32 -p tcp --sport 80 "

if [ -f /etc/config/gatewayd ]
then
	nat_remote_host=`python -c 'import json; print json.load(open("/etc/config/gatewayd"))["global"]["remote_nat_ipaddr"]'`
	nat_remote_port=`python -c 'import json; print json.load(open("/etc/config/gatewayd"))["global"]["remote_nat_port"]'`
fi

if [ -f /etc/config/natd ]
then
	natd_allowed_hosts=`python -c 'import json; jp = json.load(open("/etc/config/natd")); print "\n".join(jp["global"]["allowed_hosts"] if "allowed_hosts" in jp["global"] else ["127.0.0.1/32"])'`
	natd_interface=`python -c 'import json; jp = json.load(open("/etc/config/natd")); print jp["global"]["interface"] if "interface" in jp["global"] else "lo"'`
	natd_remote_port=`python -c 'import json; jp = json.load(open("/etc/config/natd")); print jp["global"]["remote_nat_port"] if "remote_nat_port" in jp["global"] else "32000"'`
fi

error_chk()
{
if [ $? = 0 ]
then
echo " - Success";
else
echo " - Failed";
fi
}

Q="/dev/null 2>&1"

cleanup_rt()
{
	ip rule del fwmark $ip_mark table $ip_table_id > /dev/null 2>&1
	ip route del table $ip_table_id > /dev/null 2>&1
}

cleanup_chains()
{
	iptables -w -D FORWARD -i $ipif -j ACCEPT > /dev/null 2>&1
    iptables -w -F WAN_FWD > /dev/null 2>&1
	iptables -w -X WAN_FWD > /dev/null 2>&1
    iptables -w -D FORWARD -j WAN_FWD > /dev/null 2>&1
}

cleanup_rules()
{
	iptables -w -t mangle -F OUTPUT 
	# TODO: Replace all the following with
	# iptable -F VCMP_IN_ACL
	# iptable -F VCMP_OUT_ACL
    iptables -w -D VCMP_IN_ACL -i $1 -p tcp --dport 22 -j ACCEPT
    iptables -w -D VCMP_IN_ACL -i $1 -p tcp --dport 443 -j ACCEPT
    iptables -w -D VCMP_IN_ACL -i $1 -p tcp --sport 443 -j ACCEPT
    [ -n "$nat_remote_port" -a -n "$nat_remote_host" ] && iptables -w -D VCMP_IN_ACL -i $1 -p tcp -s $nat_remote_host --sport $nat_remote_port -j ACCEPT
    iptables -w -D VCMP_IN_ACL -i $1 -p udp --sport 53 -m state --state ESTABLISHED -j ACCEPT
    iptables -w -D VCMP_IN_ACL -i $1 -p tcp -s 10.0.0.0/8 --dport 5666 -j ACCEPT
    iptables -w -D VCMP_IN_ACL -i $1 -p icmp -j ACCEPT
    iptables -w -D VCMP_IN_ACL -i $1 -p tcp --sport 80 -j ACCEPT
    iptables -w -D VCMP_IN_ACL -i $1 -p tcp --sport 22 -j ACCEPT
    iptables -w -D VCMP_IN_ACL -i $1 -p esp -j DROP
    iptables -w -D VCMP_IN_ACL -i $1 -p udp --sport 123 -m state --state ESTABLISHED -j ACCEPT
    iptables -w -D VCMP_OUT_ACL -o $1 -p tcp --dport 443 --tcp-flags RST RST -j DROP
    iptables -w -D VCMP_OUT_ACL -o $1 -p tcp --dport 80 --tcp-flags RST RST -j DROP
    iptables -w -D VCMP_OUT_ACL -o $1 -p tcp --dport 22 --tcp-flags RST RST -j DROP
    iptables -w -D VCMP_OUT_ACL -o $1 -p icmp --icmp-type 3/2  -j DROP
}

init()
{
	echo -n "Enabling ip forwarding"
	echo 1 > /proc/sys/net/ipv4/ip_forward
	error_chk;
	echo -n "Disabling rp_filter on $1"
	echo 0 > /proc/sys/net/ipv4/conf/$1/rp_filter
	error_chk;
	echo -n "Disabling rp_filter on all"
	echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter
	error_chk;
	echo -n "Setting IP local port range 15000 - 19000"
	echo "15000 19000" > /proc/sys/net/ipv4/ip_local_port_range
	error_chk;

    if [ -f "/tmp/.VCG_UPGRADE_FW" ]
    then
        # This is to prevent local stack from sending TCP resets while gwd is getting upgraded.
        iptables -w -D OUTPUT -p tcp --tcp-flags RST RST -j DROP
        logger -t VCG_UPGRADE_FW "Unsetting rule to drop TCP RST to prevent local stack from sending TCP resets during upgrade ... $?"
        
        # This is to prevent local stack from sending ICMP dest unreachable for UDP flows while gwd is getting upgraded.
        iptables -w -D OUTPUT -p icmp -m icmp --icmp-type 3 -j DROP
        logger -t VCG_UPGRADE_FW "Unsetting rule to drop ICMP DestUnrch to prevent local stack from ICMP dest unreachable for UDP flows during upgrade ... $?"
        rm /tmp/.VCG_UPGRADE_FW
    fi

	for i in $wan;
	do
		cleanup_rules $i;
	done
	cleanup_chains;
	cleanup_rt;
}

init $ipif;

#SELF_IP=`ifconfig eth0 | grep "inet addr" | cut -d ':' -f 2 | cut -d ' ' -f 1`;
#echo $SELF_IP

setup_if_mtu()
{
	echo -n "[$0 INFO] Setting mtu to $2 for $1";
	/sbin/ifconfig $1 mtu $2 up
	error_chk;
	echo -n "[$0 INFO] Setting txqueuelen to 4096 for $1";
	/sbin/ifconfig $1 txqueuelen 4096
	error_chk;
}

setup_if_opts()
{
	echo -n "[$0 INFO] Disabling GRO and LRO for $1";
	ethtool -K $1 gro off lro off
	error_chk;
}

setup_if()
{
	echo -n "[$0 INFO] Setting interface $1 UP";
	/sbin/ifconfig $1 $2 netmask $3
}

setup_rt()
{
	echo -n "[$0 INFO] Setting up policies for interface $1";
	ip rule add fwmark $ip_mark table $ip_table_id
	error_chk;

	echo -n "[$0 INFO] Setting up policies for interface $1";
	ip route add default dev $1 table $ip_table_id
	error_chk;

	da_nw=`cat "$GWD_CONF" | python -c 'import sys, json;  arr=json.load(sys.stdin)["global"]; print arr["debug_access_nw"]' | cut -d '/' -f 1`	
	da_nm=`cat "$GWD_CONF" | python -c 'import sys, json;  arr=json.load(sys.stdin)["global"]; print arr["debug_access_nw"]' | cut -d '/' -f 2`	
	if [ -n "$da_nw" ] && [ -n "$da_nm" ]
	then
		logger -t GWD "route add -net $da_nw netmask $da_nm dev $1"
		route add -net $da_nw netmask $da_nm dev $1
	else
		logger -t GWD "route add -net $da_nw netmask $da_nm dev $1"
		route add -net 169.254.1.0 netmask 255.255.255.0 dev $1
	fi
}

setup_acl_input()
{
	iptables -w -I VCMP_IN_ACL -i $1 -p tcp --dport 22 -j ACCEPT
    iptables -w -I VCMP_IN_ACL -i $1 -p tcp --dport 443 -j ACCEPT
    iptables -w -I VCMP_IN_ACL -i $1 -p tcp --sport 443 -j ACCEPT
    [ -n "$nat_remote_port" -a -n "$nat_remote_host" ] && iptables -w -I VCMP_IN_ACL -i $1 -p tcp -s $nat_remote_host --sport $nat_remote_port -j ACCEPT
    iptables -w -I VCMP_IN_ACL -i $1 -p udp --sport 53 -m state --state ESTABLISHED -j ACCEPT
    iptables -w -I VCMP_IN_ACL -i $1 -p tcp -s 10.0.0.0/8 --dport 5666 -j ACCEPT
    iptables -w -I VCMP_IN_ACL -i $1 -p icmp -j ACCEPT
    iptables -w -I VCMP_IN_ACL -i $1 -p tcp --sport 80 -j ACCEPT
    iptables -w -I VCMP_IN_ACL -i $1 -p tcp --sport 22 -j ACCEPT
    iptables -w -I VCMP_IN_ACL -i $1 -p udp --sport 123 -m state --state ESTABLISHED -j ACCEPT
    iptables -w -I VCMP_IN_ACL -i $1 -p esp -j DROP
    iptables -w -I VCMP_OUT_ACL -o $1 -p tcp --dport 443 --tcp-flags RST RST -j DROP
    iptables -w -I VCMP_OUT_ACL -o $1 -p tcp --dport 80 --tcp-flags RST RST -j DROP
    iptables -w -I VCMP_OUT_ACL -o $1 -p tcp --dport 22 --tcp-flags RST RST -j DROP
    iptables -w -I VCMP_OUT_ACL -o $1 -p icmp --icmp-type 3/2  -j DROP
}

setup_acl_fwd()
{
	iptables -w -I FORWARD -i $ipif -j ACCEPT
}

if [ "$1" = "1" ]
then

	if [ -n "$ipif_mtu" ]
	then
		setup_if_mtu $ipif $ipif_mtu
	fi

	setup_acl_fwd;

	for i in $wan;
	do
		setup_if_mtu $i $wan_mtu
		setup_if_opts $i
		setup_acl_input $i
	done
	for i in $wan_phys_if;
	do
		setup_if_opts $i
	done
	setup_rt $ipif


	if [ -n "$natd_interface" ]
	then
                iptables -w -I VCMP_IN_ACL -i lo -p tcp --sport $natd_remote_port -j ACCEPT
		for src in $natd_allowed_hosts
		do
		      iptables -w -I VCMP_IN_ACL -p tcp -i $natd_interface -s $src --dport $natd_remote_port -j ACCEPT
		done
	fi

fi
