#!/bin/sh
/proc/boot/pathtrust '!/accounts/1000/shared/misc/berrycore/lib/python3_ntoarmv7-qnx-static/tools/python3/python3.11'
export PYTHONHOME=/accounts/1000/shared/misc/berrycore/lib/python3_ntoarmv7-qnx-static
exec /accounts/1000/shared/misc/berrycore/lib/python3_ntoarmv7-qnx-static/tools/python3/python3.11 /accounts/1000/shared/misc/berrycore/probe_rootasrpp.py
