#!/usr/bin/env bash

/opt/vc/bin/cleanup_cores.sh
/usr/lib/quagga/bgpd --daemon -A 127.0.0.1
