#!/usr/bin/python

# Usage: mkdiagbundle [-b] [-d dir]* [-c "cmd" ]* -o diagbundle.tar.gz

import sys
import os.path
sys.path.insert(0, '/opt/vc/lib/python')
# Source tree:
sys.path.insert(1, os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../pylibs'))

import mgd.config
import mgd.logconfig
import mgd.diag

import argparse

# Helper for manifest (-m) arguments:
class StoreManifestEntry(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        n, v = values.split('=')
        namespace.manifest[n] = v

# Parse arguments
parser = argparse.ArgumentParser(description="Create a diagnostic dump")
parser.add_argument('-o', '--output', help="Output file", required=True)

parser.add_argument('-m', '--manifest', action=StoreManifestEntry, default={},
                    help="Additional Manifest Entry - key=value")
parser.add_argument('-d', '--dir', action='append', default=[],
                    help="Include additional specified directory in dump")
parser.add_argument('-D', '--obfuscated-dir', action='append', default=[],
                    help="Include additional specified directory, obfuscated, in dump")
parser.add_argument('-c', '--cmd', action='append', default=[],
                    help="Include output of additional specified command in dump")
parser.add_argument('-p', '--core-pattern', action='append', default=[],
                    help="Specify additional core-file name pattern")
parser.add_argument('-n', '--num-cores', type=int, default=-1,
                    help="Maximum number of cores to include (default -1 == all cores)")
parser.add_argument('-b', '--binary', action='append', default=[],
                    help="Include additional specified binary in dump if including binaries")
parser.add_argument('-s', '--max-size', type=int, default=-1,
                    help="Maximum size of diag bundle (default -1 == unlimited)")
parser.add_argument('--no-binaries', action='store_true',
                    help="Do not include key binaries in dump")
args = parser.parse_args()

mgd.config.load_configs()
#print mgd.config.config.state
logger = mgd.logconfig.getLogger()
b = mgd.diag.LogDiagBundle(logger,
                           manifest=args.manifest,
                           dirs=args.dir, obfuscated_dirs=args.obfuscated_dir,
                           commands=args.cmd, core_patterns=args.core_pattern,
                           binaries=args.binary,
                           include_binaries=not args.no_binaries,
                           max_cores=args.num_cores,
                           max_zip_size=args.max_size)
b.generate_bundle(args.output)

