#!/bin/sh

if [ "$1" = "-w" ]; then
    WAIT=1
    shift
fi

UNCOMPR_CORE_DIR=/tmp

if [ -x /opt/vc/sbin/gwd ]; then
    # Gateway: no /velocloud, save at /var/core
    DEFAULT_COMPR_CORE_DIR="/var/core"
else
    if ! mount | grep -q ' on /velocloud .*rw,' ; then
        # Unknown or single-partition edge platform?
        DEFAULT_COMPR_CORE_DIR="/tmp"
    else
        DEFAULT_COMPR_CORE_DIR="/velocloud/core"
    fi
fi

COMPR_CORE_DIR=${1:-$DEFAULT_COMPR_CORE_DIR}

FATAL()
{
    echo "$@" 1>&2
    logger -t cleanup_cores "$@"
    exit 1
}

COLLECT_DEPS()
{
    COREFILE="$1"

    /opt/vc/bin/analyze_core.sh -d "$COREFILE" | sed -e 's;^;deps;'
}

SPECIAL_EXES="edged gwd natd"
SPECIAL_EXES_RE="$(echo $SPECIAL_EXES | sed -e 's; ;|;g')"
MAX_SPECIAL_CORES=3
MAX_OTHER_CORES=1

CLEANUP_CORE_DIR()
{
    (
    cd $COMPR_CORE_DIR

    SPL_CORES=""
    for PFX in $SPECIAL_EXES ; do
	SPL_CORES="$SPL_CORES $(ls -t $PFX.*.core.tgz 2>/dev/null | head -$MAX_SPECIAL_CORES)"
    done
    SPL_CORES=" $(echo $SPL_CORES) "
    OTHER_CORES="$(ls -t *.core.tgz | egrep -v "${SPECIAL_EXES_RE}" | head -$MAX_OTHER_CORES)"
    OTHER_CORES=" $(echo $OTHER_CORES) "

    if [ "$COMPR_CORE_DIR" = "$UNCOMPR_CORE_DIR" ]; then
        # compressed cores left in /tmp: be careful about deleting other *.cores
        FILESTOEXAMINE=`echo *.core.tgz`
    else
        FILESTOEXAMINE=`echo *.core*`
    fi
    FILESTODELETE=
    for F in $FILESTOEXAMINE ; do
	if expr "$SPL_CORES" : ".* $F " > /dev/null; then
	    : skip
	elif expr "$OTHER_CORES" : ".* $F " > /dev/null; then
	    : skip
	else
	    FILESTODELETE="$FILESTODELETE $F"
	fi
    done

    if [ ! -z "$FILESTODELETE" ]; then
        logger -t cleanup_cores "Deleting old cores $FILESTODELETE"
        rm -rf $FILESTODELETE
    fi
    )
}

COMPRESS_CORE()
{
    TAR=`which tar`
    if [ "`readlink $TAR`" = "busybox" ]; then
        SPARSE=
    else
        SPARSE=S
    fi
    CORE="$1"
    /opt/vc/bin/analyze_core.sh "$CORE" > "$CORE"-info.txt 2>&1
    COREPID=`echo "$CORE" | awk -F. '{print $(NF-3);}'`
    if [ -d debug/"$COREPID" ]; then
            DEBUGDUMPDIR="debug/$COREPID"
    else
            DEBUGDUMPDIR=
    fi
    EXENAME=`/opt/vc/bin/analyze_core.sh -e "$CORE"`
    # Normalize core bundle name if possible
    if [ ! -z "$EXENAME" ] ; then
        EXEBASE="${EXENAME##*/}"
        CORESUF=`expr "$CORE" : ".*\(\.[0-9]*\.[0-9]*\.[0-9]*\.core\)"`
        TARBASE="$EXEBASE$CORESUF"
    else
        TARBASE="$CORE"
    fi
    # for gwd and natd, collect dependent libraries and include gwd here.
    # for edged, leave as is for now - this bloats up core packages a lot.
    if echo "$EXENAME" | egrep '(gwd|natd)' > /dev/null; then
        DEPS=`COLLECT_DEPS "$CORE"`
        DEPS="deps$EXENAME $DEPS"
        rm -rf deps
        ln -s / deps
    fi
    STARTTIME=`date +%s`
    tar c${SPARSE}zhf $COMPR_CORE_DIR/"$TARBASE".tgz "$CORE"-info.txt $DEBUGDUMPDIR "$CORE" $DEPS
    rm -rf "$CORE" "$CORE"-info.txt $DEBUGDUMPDIR deps
    ENDTIME=`date +%s`

    logger -t cleanup_cores "Compressed $CORE in $((ENDTIME-STARTTIME)) seconds"

    # After compressing a new core, clean up old core bundles that are not needed
    CLEANUP_CORE_DIR
}

mkdir -p $COMPR_CORE_DIR
cd $UNCOMPR_CORE_DIR

(
    # The meat of the script, executed under an flock to prevent
    # concurrent script runs in case edged or gwd crash several
    # times in quick succession.

    # Take an exclusive lock of fd 9 (connected to /tmp/.cleanup.lock below)
    # Wait upto 60 seconds for any concurrent scripts to finish
    #FLOCK_WAIT="-w 60"   # busybox flock doesn't support this
    FLOCK_WAIT=""
    flock -x $FLOCK_WAIT 9 || FATAL "Timed out waiting for other cleanup_cores"

    CORES_TO_COMPRESS=`ls -t *.core`
    for U in $CORES_TO_COMPRESS; do
        COMPRESS_CORE "$U"
    done
) < /dev/null > /tmp/cleanup.out 2>&1 9> /tmp/.cleanup.lock &

if [ "$WAIT" = "1" ]; then
    wait
fi
