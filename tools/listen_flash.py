#!/usr/bin/env python3
import subprocess, sys, time, os, re

LDR = '/tmp/opencode/loaders_x/pp_cap/loader_8D002C0A-00.bin'
MCT = '/tmp/opencode/mct_raw.bin'
BBL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bblink.py')
BBL = '/home/stanw47/Documents/blackberry-research/tools/bblink.py'

def run(argv, timeout=200):
    return subprocess.run([sys.executable, BBL, '--loader', LDR] + argv, capture_output=True, text=True, timeout=timeout)

def present(out):
    m = re.search(r'PIDs: \[([^\]]*)\]', out or '')
    if not m:
        return False
    return [p.strip().strip("'").strip('"') for p in m.group(1).split(',') if p.strip()]

print('listener: waiting for BlackBerry device (plug in the powered-off Passport)', flush=True)
checked = 0
while True:
    try:
        r = run(['probe', '--timeout', '2'], timeout=30)
    except Exception as e:
        print('probe error: %r' % e, flush=True)
        time.sleep(1)
        continue
    pids = present(r.stdout) or present(r.stderr)
    if not pids:
        checked += 1
        if checked % 60 == 0:
            print('... still listening (checked %d)' % checked, flush=True)
        time.sleep(1)
        continue
    pid = pids[0]
    print('device detected PIDs=%s' % pids, flush=True)
    if pid not in ('0001', '8001'):
        print('  PID %s is not loader mode (BootROM=0001 / RAM-loader=8001). '
              'If device is in OS mode: power it OFF and replug while this listens.' % pid, flush=True)
        time.sleep(1)
        continue
    print('running READ-ONLY info session', flush=True)
    r2 = run(['info', '--out', MCT, '--keep'], timeout=300)
    print(r2.stdout, flush=True)
    if r2.stderr:
        print(r2.stderr, flush=True)
    if os.path.exists(MCT):
        print('MCT saved:', MCT, os.path.getsize(MCT), 'bytes', flush=True)
        print('done - read-only session complete, no writes. keep listening for next replug.', flush=True)
    else:
        print('info session had no usable result - still listening.', flush=True)
    time.sleep(1)