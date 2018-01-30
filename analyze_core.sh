#!/bin/sh

DEPS=
PRINTEXE=
while getopts de opt ; do
    case "$opt" in
        d) DEPS=1 ;;
        e) PRINTEXE=1 ;;
        [?]) echo >&2 "Usage: $0 [-d] [-e] corefilename" ; exit 1 ;;
    esac
done
shift $((OPTIND-1))

# $1 == core file name

if [ ! -r "$1" ]; then
    1>&2 echo Usage: $0 corefile
    exit 1
fi

if [ -x /usr/bin/file ]; then
    CMD=`file $1 | grep 'core file' | sed -e "s/^[^']*'//" -e "s/'[^']*$//"`
    CMD=${CMD%% *}
    if [ ! -z "$CMD" ]; then
        EXENAME=`which $CMD`
    fi
fi

if [ -z "$EXENAME" ]; then
    # try readelf
    EXENAME=`readelf -n $1 | sed -n -e 's;^ */;/;gp' 2>/dev/null | head -1 2>&1`
fi

if [ ! -r "$EXENAME" ]; then
    # unable to read the executable
    1>&2 echo Unable to locate executable of core: $EXENAME
    exit
fi

if [ "$PRINTEXE" = 1 ]; then
    echo $EXENAME
    exit 0
fi

if [ "$DEPS" = 1 ]; then
    echo "info sharedlibrary" |\
        gdb $EXENAME $1 2>/dev/null |\
        sed -n -e '1,/Shared Object Library/d' \
            -e 's;[a-z][a-z]*/\.\./;;' \
            -e '/\//s;^[^/]*/;/;p'
    exit 0
fi

# The real analysis
. /opt/vc/etc/vc-version.properties
echo OS_VERSION=$VC_GIT_TAG

echo EXECUTABLE=$EXENAME
EXEBASE=${EXENAME##*/}
if [ "$EXEBASE" = "edged" -o "$EXEBASE" = "gwd" -o "$EXEBASE" = "natd" ]; then
    EXEVER=`"$EXENAME" -v 2>&1 | grep -i 'Build rev' | sed -e 's/^.*:[[:space:]]*//'`
    echo `echo $EXEBASE | tr a-z A-Z`_VERSION=$EXEVER
fi
if [ ! -x /usr/bin/gdb ]; then
    1>&2 echo No gdb available to analyze core
    return
fi

# Emit a basic core analysis while we still have the original core
echo ""
echo "------------------------------------------------------------"
GDBSCRIPT=/tmp/gdbscript-$$
trap "rm $GDBSCRIPT" 0 1 2 3 8 15
cat > $GDBSCRIPT <<EOF
set pagination off
set height 0
set width 0
define xtrace
bt full
echo \n----\n
end

echo \n\f====================== CURRENT THREAD =========================\n\n
bt full
echo \n\f======================= SHARED LIBS ===========================\n\n
info sharedlibrary
echo \n\f========================= THREADS =============================\n\n
info threads
echo \n\f==================== FULL STACK TRACES ========================\n\n
thread apply all xtrace
echo \n\n
EOF

# Run GDB with the script above
gdb -nx -batch -x $GDBSCRIPT "$EXENAME" "$1"
