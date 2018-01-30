#!/usr/bin/python

#
# Usage: python activate.py [-j] [-f] [-s vcoserver] activation_key
#

import sys
import os
sys.path.insert(0, '/opt/vc/lib/python')
# Source tree:
sys.path.insert(1, os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../pylibs'))

import mgd.act
import mgd.options
import mgd.logconfig
import mgd.config
import mgd.mgd
import mgd.mgdutils

import pyutil.utils

import argparse
import time
import pyutil.pki as pki

logger=mgd.logconfig.getLogger('activation')

device_name=mgd.options.device_name

# Load standard config if it exists, to see if it's already activated
mgd.config.load_configs(logger)
previously_activated = mgd.config.config.state.get('activated')

# Load new default activation options
ACTIVATION_CONFIG_FILE = mgd.config.CONFIG_FILE + ".activation"
#Don't remove existing .edge.info.activation - it has accumulated errors.
#pyutil.utils.quiet_remove(ACTIVATION_CONFIG_FILE)
mgd.config.load_configs(logger, ACTIVATION_CONFIG_FILE)

default_vco = mgd.config.mpconfig.get_primary_vco()
sleep_before_reboot = 5

parser = argparse.ArgumentParser(description='Activate an %s.' % device_name)
parser.add_argument("-j", "--asJson", help="return status as JSON string",
                    action="store_true")
parser.add_argument("-p", "--progress", help="show progress of activation",
                    action="store_true", default=True)
parser.add_argument("-o", "--outfile", help="file for progress output (only last message)")
parser.add_argument("-f", "--force", help="force re-activation",
                    action="store_true")
parser.add_argument("-r", "--resume-download",
                    help="Resume after post-activation download failure",
                    action="store_true")
parser.add_argument("-s", "--server",
                    help="VCO address for activation (default = %s)" % (default_vco),
                    default=default_vco)
parser.add_argument("-m", "--model",
                    help="Override model reported for activation")
parser.add_argument("-i", "--ignorecerterror",help="Ignore certificate errors",
                    action="store_true")
parser.add_argument('activation_key', nargs='?',
                    help='your activation key from the VeloCloud Orchestrator')
args = parser.parse_args()

if not args.resume_download and not args.activation_key:
    raise Exception("Activation key is required")

# Check to see if it's already been activated (accidental
# re-invocation of activate). This is a stop-gap check; eventually,
# we want to be able to do a "safe re-activate" any time.
if previously_activated:
    # Already activated
    if not args.force:
        raise Exception('%s has already been activated' % mgd.options.device_name)
    # MGD was previously running in an activated state;
    # Make sure to restart it after re-activation
    restart_mgd = True

# Normalize the server name
if args.server is not None:
    newconfig = {
        "managementPlane": {
            "module":"managementPlane",
            "version":"0",
            "moduleId":"0",
            "data":{"managementPlaneProxy":{"primary":args.server}},
        }
    }
    # Don't save this: if activation succeeds, _it_ will save the config
    mgd.config.update_configuration(newconfig, save=False)

if device_name == "Edge" and args.server:
    # Make sure we can reach the VCO
    setup_cmd = ["/opt/vc/bin/setdefroute.sh", "-f", args.server]
    logger.info("Executing command %s", setup_cmd)
    mgd.mgdutils.os_command(logger, setup_cmd)

mgd_killed = False
if not args.resume_download and mgd.options.device == 'edge':
    # a full activation attempt; kill mgd and any children
    pyutil.utils.touch("/tmp/mgd.DISABLED")
    os.system("killall mgd")
    activate_pids_str = mgd.mgdutils.os_command_output("pgrep activate.py || true",shell=True)
    mypid = os.getpid()
    for s in activate_pids_str.split():
        try:
            if int(s) != mypid:
                os.kill(int(s), 15)
        except:
            pass
    mgd_killed = True

restart_mgd = False
logger.info("Activating %s, args = %s" % (device_name,args))
daemon = mgd.mgd.Mgd(logger)

# Now activate the device:

try:
    pki.pki_init(True,args.ignorecerterror)
    result = mgd.act.activate(daemon, args.activation_key, args.force,
                              args.resume_download, args.asJson, args.outfile,
                              args.progress, args.model, args.ignorecerterror)
except Exception as e:
    print "Error in activation: %s" % e
    result = {"activated": False}

if result["activated"]:
    pki.save_vco_cert_validation_policy(args.ignorecerterror) # Activation was successfull, it's OK to save the VCO certificate validation policy now
    if result.get("reboot_required"):
        # TODO: restart here, or in activation UI?
        if not args.asJson:
            print "Rebooting in %f seconds after software installation during download" % sleep_before_reboot
        try:
            time.sleep(sleep_before_reboot)
        except:
            pass
        logger.info("Rebooting after software installation during download")
        os.system("reboot")
    # Rename the activation edge.info to its original name
    pyutil.utils.quiet_remove(mgd.config.CONFIG_FILE)
    try:
        os.rename(ACTIVATION_CONFIG_FILE, mgd.config.CONFIG_FILE)
    except Exception as e:
        # activation failed!
        logger.error("Unable to save activation configuration file: %s", str(e))
        pyutil.utils.quiet_remove(ACTIVATION_CONFIG_FILE)
        sys.exit(1)

elif result.get("pending_update") and not args.resume_download:
    restart_mgd = True

if restart_mgd and not mgd_killed:
    # restart mgd to pick up new activation state
    os.system("(sleep 2; killall -g mgd; sleep 2; killall -9 -g mgd) &")
    # restart of edged moved to mgd.Mgd.start()

# Allow mgd to start, in case we had stopped it above
pyutil.utils.quiet_remove("/tmp/mgd.DISABLED")

if not result['activated']:
    sys.exit(1)
