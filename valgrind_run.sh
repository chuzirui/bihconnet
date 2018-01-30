#!/bin/sh

VALGRIND_ARG1="--tool=memcheck --track-fds=yes"
VALGRIND_ARG2="--num-callers=20 --leak-check=full --error-limit=no --show-reachable=yes"
EDGED_DISABLE=/tmp/edged.DISABLED
GWD_DISABLE=/tmp/gwd.DISABLED
VALGRIND_RUN=/tmp/.valgrind_run

cleanup() {
    echo "Valgrind cleanup"
    if [ "$EDGED" = 1 ]; then
        rm -f ${EDGED_DISABLE}
    fi
    if [ "$GWD" = 1 ]; then
        rm -f ${GWD_DISABLE}
    fi
    rm -f ${VALGRIND_RUN}
    exit 0
}

#Register for SIGHUP, SIGINT, SIGTERM
trap cleanup 1 2 15

while getopts eg opt ; do
    case "$opt" in
        e) EDGED=1 ;;
        g) GWD=1 ;;
        [?]) echo >&2 "Usage: $0 [-e] [-g] vglog_filename" ; exit 1 ;;
    esac
done
shift $((OPTIND-1))

if [ "$EDGED" = 1 ] && [ "$GWD" = 1 ]; then
    1>&2 echo "Error: either of -e or -g allowed"
    exit 2
fi

if [ ! -r /usr/bin/valgrind ]; then
    # unable to find valgrind tool
    1>&2 echo "Error: Unable to locate valgrind tool"
    exit 2
fi

#Stop vc process monitor
/opt/vc/bin/vc_procmon stop

echo "vc_procmon stop done"

#create a valgrind run status file
touch ${VALGRIND_RUN}

/opt/vc/bin/vc_procmon start
#Setup for valgrind run
echo -n "Start Valgrind run"
if [ "$EDGED" = 1 ]; then
    echo " for EDGED params - logfile: $1"
    #Disable edged process retart using vc_procmon
    touch ${EDGED_DISABLE}
    EXENAME="/opt/vc/sbin/edged -F /etc/config/edged"
fi

if [ "$GWD" = 1 ]; then
    echo " for GWD params - logfile: $1"
    #Disable edged process retart using vc_procmon
    touch ${GWD_DISABLE}
    EXENAME="/opt/vc/sbin/gwd -F /etc/config/gatewayd"
fi
touch "$1"
# $1 == core file name
#valgrind run
/usr/bin/valgrind ${VALGRIND_ARG1} --log-file="$1" ${VALGRIND_ARG2} ${EXENAME}

