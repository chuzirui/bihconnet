#!/usr/bin/env bash

# This is a mutexmon exit
if [ "$PROCMON_RETCODE" == "-24" ];
then
   epoch=`date +'%s'`
   echo {\"last_crash\": $epoch} > /velocloud/state/mutexmon.json
fi

# clean up cores (launches quickly into background)
/opt/vc/bin/cleanup_cores.sh

# Gateway is saying that dpdk cannot be started on this gateway for whatever reason,
# and its a "hard" failure, theres no point re-attempting dpdk start. So just
# stop dpdk and disable it forever
name=`cat /opt/vc/etc/dpdk.json | sed -rn 's/^.*\"status\":.*\"(.*)\",/\1/p'`
if [ $name == "Aborted" ];
then
  /opt/vc/bin/vc_dpdk.sh stop
  /opt/vc/bin/vc_dpdk.sh disable
fi

