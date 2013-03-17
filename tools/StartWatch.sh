#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname $(readlink -e "${BASH_SOURCE[0]}") )" && pwd )"

FILENAME="BanBot.py";
[ "$1" != "" ] && FILENAME=$1;

ShutdownScript() {
	echo Exiting StartWatch.sh;
	killwait onfilechange;
	exit 0;
}

trap ShutdownScript SIGINT

echo $SCRIPT_DIR;

# onfilechange . pklib -- killwait BanBot.py &

while [ true ]; do
	$SCRIPT_DIR/$FILENAME -n 2>&1 || { echo "Failed to start, sleeping 5 seconds..." && sleep 5; } && sleep .5;
done;
