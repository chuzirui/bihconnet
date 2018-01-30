#!/bin/sh

# Binary name (edged/gwd) is given as input arg 

if [ "$#" -eq 0 ] || [ "$#" -gt 1 ]; then
	echo "Usage: ./script [edged|gwd]"
	exit 0
fi

if [ "$1" != "edged" ] && [ "$1" != "gwd" ]; then
	echo "Usage: ./script [edged|gwd]"
	exit 0
fi

pid=`pgrep -f /opt/vc/sbin/$1`
echo $pid
if [ -z "$pid" ]; then
	echo "$1 : process not running"
	exit 0
fi

dbg_dir=/tmp/debug/$pid
mkdir -p $dbg_dir 
cmd_dir=/opt/vc/bin/

# List all commands to be executed

if [ "$1" = "edged" ]; then

	$cmd_dir/dispcnt -a > $dbg_dir/dispcnt
	$cmd_dir/debug.py --bw_testing_dump > $dbg_dir/bw_testing_dump
	$cmd_dir/debug.py --chat_stats > $dbg_dir/chat_stats
	$cmd_dir/debug.py --clock_sync > $dbg_dir/clock_sync
	$cmd_dir/debug.py --current_apps > $dbg_dir/current_apps
	$cmd_dir/debug.py --cwp_print_cache > $dbg_dir/cwp_print_cache
	$cmd_dir/debug.py --dec > $dbg_dir/dec
	$cmd_dir/debug.py --dns_name_cache > $dbg_dir/dns_name_cache
	$cmd_dir/debug.py --flow_dump > $dbg_dir/flow_dump
	$cmd_dir/debug.py --jitter > $dbg_dir/jitter
	$cmd_dir/debug.py --link_stats > $dbg_dir/link_stats
	$cmd_dir/debug.py --path_stats > $dbg_dir/path_stats
	$cmd_dir/debug.py -v --firewall_dump > $dbg_dir/verbose_firewall_dump
	$cmd_dir/debug.py -v —-link_stats > $dbg_dir/verbose_link_stats
	$cmd_dir/debug.py -v —-path_stats > $dbg_dir/verbose_path_stats
	$cmd_dir/debug.py -v --biz_pol_dump > $dbg_dir/verbose_biz_pol_dump
	$cmd_dir/debug.py --routes > $dbg_dir/routes
	$cmd_dir/debug.py --dce_clients > $dbg_dir/dce_clients
	$cmd_dir/debug.py --dce_edge > $dbg_dir/dce_edge
	$cmd_dir/debug.py --user_route_dump > $dbg_dir/user_route_dump
	$cmd_dir/debug.py --local_subnets > $dbg_dir/local_subnets
	$cmd_dir/debug.py --ike > $dbg_dir/ike
	$cmd_dir/debug.py --static_routes > $dbg_dir/static_routes
	$cmd_dir/debug.py --bwcap > $dbg_dir/bwcap
	$cmd_dir/debug.py --dynbwdbg > $dbg_dir/dynbwdbg
	$cmd_dir/debug.py --handoffqdbg > $dbg_dir/handoffqdbg
	$cmd_dir/debug.py --pktsqed > $dbg_dir/pktsqed
	$cmd_dir/debug.py --hfscdbg link none 0 > $dbg_dir/hfsc_link_none_0
	$cmd_dir/debug.py --whitelist > $dbg_dir/whitelist
	$cmd_dir/debug.py --verbose_arp_dump > $dbg_dir/verbose_arp_dump
	$cmd_dir/debug.py --list_vpn_endpoints > $dbg_dir/list_vpn_endpoints
	$cmd_dir/debug.py --remote_services > $dbg_dir/remote_services
	$cmd_dir/debug.py --dump_ac > $dbg_dir/dump_ac
	$cmd_dir/debug.py --pl_hier_dbg dump > $dbg_dir/pl_hier_dbg_dump
	$cmd_dir/debug.py --pmtud_dump > $dbg_dir/pmtud_dump

elif [ "$1" = "gwd" ]; then

	$cmd_dir/dispcnt -a > $dbg_dir/dispcnt
	$cmd_dir/debug.py --flow_dump > $dbg_dir/flow_dump
	$cmd_dir/debug.py --jitter > $dbg_dir/jitter
	$cmd_dir/debug.py --link_stats > $dbg_dir/link_stats
	$cmd_dir/debug.py --path_stats > $dbg_dir/path_stats
	$cmd_dir/debug.py --verbose_routes > $dbg_dir/verbose_routes
	$cmd_dir/debug.py --peers > $dbg_dir/peers
	$cmd_dir/debug.py --verbose_ike > $dbg_dir/verbose_ike
	$cmd_dir/debug.py --bwcap > $dbg_dir/bwcap
	$cmd_dir/debug.py --dce_list > $dbg_dir/dce_list
	$cmd_dir/debug.py --dynbwdbg > $dbg_dir/dynbwdbg
	$cmd_dir/debug.py --handoffqdbg > $dbg_dir/handoffqdbg
	$cmd_dir/debug.py --pktsqed > $dbg_dir/pktsqed
	$cmd_dir/debug.py --hfscdbg link none 0 > $dbg_dir/hfsc_link_none_0
	$cmd_dir/debug.py --pl_hier_dbg dump > $dbg_dir/pl_hier_dbg_dump
	$cmd_dir/debug.py --icmp_monitor > $dbg_dir/icmp_monitor
	$cmd_dir/debug.py --stale_flow_dump all > $dbg_dir/stale_flow_dump_all
	$cmd_dir/debug.py --stale_pi_dump > $dbg_dir/stale_pi_dump
	$cmd_dir/debug.py --stale_td_dump > $dbg_dir/stale_td_dump

fi

exit 0
