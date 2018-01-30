#!/bin/sh

# Usage: gencore.sh [-hvc] pid_or_program...
#
# This script takes a live core of a running process without killing it or
# otherwise disturbing it in any way (other than a short freeze for the
# actual dump).
#
# If invoked with the -c option, it will then synchronously invoke the
# cleanup_cores.sh script to compress the core file into the collected
# core location. This option can be skipped if you just want to quickly
# take a core dump on a live system while logged in, for debugging, without
# stopping the main program for a long time.
#
# The core file will be named <progname>.<pid>.<timestamp>.core, and is
# first generated in /tmp. If -c is specified, it gets compressed into
# /velocloud/core/.
#

UsageMessage()
{
    echo "Usage: $0 [-h] [-v] [-c] pid_or_procname..."
    echo "    -h    Emit this help message"
    echo "    -v    Verbose listing of activity"
    echo "    -c    Clean up cores after dumping (system-dependent)"
}

USAGE()
{
    1>&2 echo "$@"
    1>&2 UsageMessage
    exit 1
}

while getopts ":hvc" opt "$@"; do
    case $opt in
        h) UsageMessage; exit 0 ;;
        c) COMPRESS_CORES=1 ;;
        v) VERBOSE=1 ;;
        \?) if [ "$OPTARG" = "?" ]; then
                UsageMessage
                exit 0
            else
                USAGE Invalid option -$OPTARG
            fi ;;
        :)  USAGE Option -$OPTARG requires an argument ;;
    esac
done
shift $((OPTIND-1))
if [ ${#@} -eq 0 ]; then
    USAGE
fi

GenerateCore()
{
    PID="$1"
    COREFILENAME="/tmp/$2.$1.$3.core"
    if [ "$VERBOSE" = "1" ]; then
        echo "Generating core for $2 pid $1"
    fi
    gdb -nx -nw -batch-silent \
        -ex "set pagination off" \
        -ex "set height 0" \
        -ex "set width 0" \
        -ex "attach $PID" \
        -ex "gcore $COREFILENAME" \
        -ex "detach" \
        < /dev/null > /dev/null 2>&1
}

for PID in "$@" ; do
    if [ ! -d /proc/"$PID" ]; then
        PID=`pidof -- "$PID"`
    fi
    if [ -z "$PID" ]; then
        1>&2 echo Invalid process or PID $PID; ignored
    fi
    EXENAME=`readlink /proc/"$PID"/exe`
    EXENAME=${EXENAME##*/}
    TS=`date +%s`

    GenerateCore $PID $EXENAME $TS
done

if [ "$COMPRESS_CORES" = 1 ]; then
    if [ "$VERBOSE" = "1" ]; then
        echo "Compressing cores after generation"
    fi
    /opt/vc/bin/cleanup_cores.sh -w
fi
