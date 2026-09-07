#!/bin/sh
# root_exec_py.sh - run python3 as root (uid0) via __root, trusting the whole python install.
PP=/proc/boot/pathtrust
PYROOT=/accounts/1000/shared/misc/berrycore/lib/python3_ntoarmv7-qnx-static
PY=$PYROOT/tools/python3/python3.11
echo "--- trusting python install subtree ---"
$PP "&$PYROOT"
echo "--- trusting python binary ---"
$PP "!$PY"
echo "--- query ---"
$PP -t "$PY"
echo "--- exec ---"
export PYTHONHOME=$PYROOT
exec "$PY" /accounts/1000/shared/misc/berrycore/probe_rootasrpp.py 2>&1
echo "exec-rc=$?"