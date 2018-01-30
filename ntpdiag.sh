#!/bin/sh

NTPDC=/usr/bin/ntpdc

echo ==== listpeers ====
echo ""
$NTPDC -c listpeers
echo ""
$NTPDC -n -c listpeers
echo ""
echo ==== peer details ====
echo ""
$NTPDC -c peers
echo ""
$NTPDC -c dmpeers
echo ""
echo ==== timerstats ====
echo ""
$NTPDC -c timerstats
echo ""
echo ==== sysinfo ====
echo ""
$NTPDC -c sysinfo
echo ""
echo ==== kerninfo ====
echo ""
$NTPDC -c kerninfo
echo ""
echo ==== loopinfo ====
echo ""
$NTPDC -c loopinfo
echo ""
