#!/usr/bin/python

import os
import re
import sys
import subprocess

#If this script returns 0, we will disable TSC timing since it's not safe when we don't know the exact tsc frequency.

#make sure the device is capapble of using TSC
#check for constant_tsc flag
command = "cat /proc/cpuinfo"
all_info = subprocess.check_output(command, shell=True)
if not "constant_tsc" in all_info:
    print 0
    sys.exit(0)

# if tsc_reliable cap is set for CPU then TSC is reliable across sockets
if not "tsc_reliable" in all_info:
    #on the edge we are always single socket, so this check doesn't matter.
    #on the gateway (Ubuntu) we have /usr/bin/lscpu.. check that we are single socket
    if os.path.isfile("/usr/bin/lscpu"):
        r=re.compile('Socket.* ([0-9.]+)')    
        proc = subprocess.Popen(['lscpu'],stdout=subprocess.PIPE)
        while True:
          line = proc.stdout.readline()
          if line != '':
            m = r.findall(line)
            if m:
                if m[0] > 1:
                    print 0
                    sys.exit(0)
          else:
            break    

#check the /etc/tsc-mhz script for the frequency
try: 
    with open("/etc/tsc-mhz", "r") as tsc_mhz_file:
        tsc_mhz = tsc_mhz_file.read().rstrip()
        print tsc_mhz
        sys.exit(0)
except (OSError, IOError):
    pass

#if that failed, check dmesg to see if we can find the frequency
r=re.compile('Refined TSC.*: ([0-9.]+)')
proc = subprocess.Popen(['dmesg'],stdout=subprocess.PIPE)
while True:
  line = proc.stdout.readline()
  if line != '':
    m = r.findall(line)
    if m:
        print "%.3f" % float(m[0])
        sys.exit(0)
  else:
    break

#couldn't determine TSC freq, return 0 so we switch to syscall timing
print 0
