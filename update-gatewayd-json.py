#!/usr/bin/python

import json

GCO = "/etc/config/gatewayd.pre-upgrade"
GC = "/etc/config/gatewayd"
PC = "/opt/vc/etc/preserve.json"

def load_contents(fileName):
	try:
		fh = open(fileName, "r")
		contents = json.load(fh);
	except:
		print "No such file: " + fileName + " Returning NULL"
		return;
	else:
		fh.close()
		print "Returning contents of " + fileName
		return contents;

GCO_contents = load_contents(GCO)
GC_contents = load_contents(GC)
PC_contents = load_contents(PC)

if (GCO_contents):
	print "Loaded contents from " + GCO + " successfully";
else:
	print "No GCO_contents. Exiting..."
	exit()

if (PC_contents):
	for section in PC_contents:
		try:
			gco_section = GCO_contents[section]
		except:
			print "No such section " + section
		else:
			for param in PC_contents[section]:
				try:
					gco_param = gco_section[param]
				except:
					print "No such param " + param + " in section " + section + " of " + GCO 
				else:
					try:
						gc_section = GC_contents[section]
					except:
						GC_contents[section] = gco_section
					else:
						gc_section[param] = gco_param

	try:
		nfh = open(GC, "w")
	except:
		print "Failed to preserve " + GC + " config"
	else:
		json.dump(GC_contents, nfh, indent=4, encoding="utf-8")
		nfh.close() 
		print "Preserved config from previous version successfully"
else:
	print "No PC_contents"
	exit()

print "==================================="
