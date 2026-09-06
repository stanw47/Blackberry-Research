# BlackBerry Classic SSH Connection on Linux (ParrotOS / Any Debian-based Distro)

Complete, reproducible procedure to establish an SSH connection to a BlackBerry Classic (SQC100) running BB10 10.3.3 from a Linux host. Tested on ParrotOS Security Edition with OpenJDK 25.

---

## 1. Enable Development Mode on the Device

Before any connection can be made, **Development Mode must be enabled on the BlackBerry Classic**:

> **Important:** Development Mode **does not persist across reboots**. If the device restarts, you must re-enable it (toggle back ON) before connecting.

1. On the device, swipe down from the top bezel → **Settings** (gear icon)
2. Navigate to **Security and Privacy** → **Development Mode**
3. Toggle **Development Mode** to **ON**
4. **Authentication:**
   - **If a Device password is already set** on the device → you will be prompted to **enter the existing Device password**.
   - **If no Device password is set** → you will be prompted to **set a new Device password** (placeholder used in this guide: `<DEVICE_PASSWORD>`).
5. Confirm the password
6. The device will display a Development Mode indicator in the system bar (usually a small bug/icon)
7. Connect the device to your Linux host via USB cable
8. The device will enumerate as a **RNDIS/Ethernet gadget** — a new network interface appears on Linux (e.g., `enxa6e4b847d44a` with IP `169.254.0.2/30`, device at `169.254.0.1`)

> **Note:** The device IP is always `169.254.0.1` on the USB/RNDIS link. The host gets `169.254.0.2` via DHCP/auto-config. The Development Mode authentication uses the **Device password** (set during initial device setup or when first enabling Dev Mode).

---

## 2. Prerequisites (Linux Host)

All commands below assume a Debian-based system (ParrotOS, Kali, Ubuntu, Debian, etc.). Adjust package manager commands for other distros.

### 2.1 System Packages
```bash
sudo apt update && sudo apt install -y \
    openjdk-17-jre-headless \
    python3-paramiko \
    python3-pip \
    openssh-client \
    netcat-openbsd \
    nmap \
    iproute2
```
- **Java 17+** (OpenJDK 17+ or 21+) — required by `blackberry-connect` (`java -Xmx512M -jar Connect.jar`). OpenJDK 25 works fine.
- **Python 3 + paramiko** — for the SSH client (QNX sshd requires specific algorithm tweaks).
- **netcat, nmap, iproute2** — for port/connectivity checks.

### 2.2 BlackBerry 10 Native SDK (for `blackberry-connect`)
The `blackberry-connect` tool is part of the **BlackBerry 10 Native SDK (NDK)**. It is a Java wrapper (`Connect.jar`) invoked via a shell script.

**Download:**
- Archive: `bbndk.win32.tools.10.3.1.12.zip` (host tools for Linux/Windows)
- Source: BlackBerry Developer site (legacy) or `archive.org/details/bbdevtools`
- Extract to a known path, e.g.:
  ```bash
  mkdir -p $HOME/priv-research
  unzip bbndk.win32.tools.10.3.1.12.zip -d $HOME/priv-research/bbndk-tools
  ```

**Key paths after extraction:**
| Component | Path |
|-----------|------|
| Wrapper script | `$HOME/priv-research/bbndk-tools/host_10_3_1_12/win32/x86/usr/bin/blackberry-connect` |
| JAR file | `$HOME/priv-research/bbndk-tools/host_10_3_1_12/win32/x86/usr/lib/Connect.jar` |
| Wrapper `.bat` | `$HOME/priv-research/bbndk-tools/host_10_3_1_12/win32/x86/usr/bin/blackberry-connect.bat` (Windows) |

The wrapper is a simple shell script:
```bash
#!/bin/sh
here=$(dirname "$0")
java -Xmx512M -jar "$here/../lib/Connect.jar" "$@"
```

### 2.3 Python SSH Helper Script (`connect_now.py`)
Save as `~/bb-repo/connect_now.py` (or any path). This script handles the QNX-specific SSH algorithm requirements.

```python
#!/usr/bin/env python3
import paramiko
import paramiko.transport as P
import os

# Monkeypatch Transport: QNX sshd only accepts RSA-SHA1 signatures.
_orig = paramiko.transport.Transport.__init__
def _new(self, *a, **kw):
    kw.setdefault('server_sig_algs', False)
    return _orig(self, *a, **kw)
paramiko.transport.Transport.__init__ = _new

# Load fresh private key (generated per-session)
key_path = os.environ.get('BBKEY', '/tmp/bb_key')
key = paramiko.RSAKey.from_private_key_file(key_path)

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    hostname='169.254.0.1',
    port=22,
    username='devuser',           # Key is provisioned to devuser
    pkey=key,
    disabled_algorithms={'pubkeys': ['rsa-sha2-512', 'rsa-sha2-256']},
    timeout=30, auth_timeout=120, banner_timeout=30,
    allow_agent=False, look_for_keys=False
)
print('SSH CONNECTED!')
stdin, stdout, stderr = c.exec_command('echo CONNECTED; uname -a', timeout=15)
print(stdout.read().decode(errors='replace'))
c.close()
```

Make it executable: `chmod +x ~/bb-repo/connect_now.py`

---

## 3. Key Concepts & Port Map

| Port | Service | Role |
|------|---------|------|
| **4455** | **qconnDoor (qconn)** | Development authentication channel. `blackberry-connect` authenticates here with the device password and pushes the SSH public key. |
| **22** | **sshd (OpenSSH)** | **Not running initially.** Started by `btool` after a successful `blackberry-connect` authentication. |
| **5555** | **adbd** | Android Debug Bridge. Open when Development Mode is on (confirms dev mode active). |

### The `btool` Boot Sequence
- `btool` is the root autorun script that runs at boot (via `/base/scripts/ota_info_pps.sh` symlink).
- `btool` **kills `qconnDoor` + `sshd`, then restarts `sshd`**.
- `btool` whitelists files via `/proc/boot/pathtrust !<path>`.
- On pre-rooted autoloaders, `btool` contains `/proc/boot/pathtrust !/base/bin/__root` to enable the setuid `__root` helper.
- **If qconnDoor (4455) is alive but SSH (22) is closed → `btool` has not run yet.**
- A successful `blackberry-connect` authentication triggers the `btool` sequence: SSH comes up, qconnDoor goes down.

---

## 4. Step-by-Step Connection Procedure

### Step 1: Verify Device State
```bash
# 1. Device on USB, Dev Mode ON (password: <DEVICE_PASSWORD>)
# 2. RNDIS interface up:
ip link show enxa6e4b847d44a

# 3. Ping test:
ping -c 2 169.254.0.1

# 4. Verify ports:
#    4455 OPEN  = qconnDoor alive, btool NOT yet run
#    22 CLOSED  = sshd not started (btool hasn't run)
#    5555 OPEN  = adbd running, dev mode confirmed

# Quick one-liner check:
ping -c1 169.254.0.1 && \
timeout 2 bash -c 'echo > /dev/tcp/169.254.0.1/4455' && echo "4455 OK" || echo "4455 DOWN"
timeout 2 bash -c 'echo > /dev/tcp/169.254.0.1/22' && echo "22 OK" || echo "22 DOWN"
```

### Step 2: Generate a Fresh 4096-bit RSA Key (Every Session)
> **CRITICAL:** The device enforces a **4096-bit minimum**. 2048-bit keys are rejected with "Provided ssh key is too small (4096-bit minimum)." A **new key must be generated for every session** — the device wipes authorized keys on disconnect/reboot.

```bash
ssh-keygen -t rsa -b 4096 -f /tmp/bb_key -N "" -q
# Output: /tmp/bb_key (private), /tmp/bb_key.pub (public)
```

### Step 3: Start `blackberry-connect` Detached (Tunnel + Key Push)
```bash
# Paths (adjust to your extraction location)
BC_BIN=$HOME/priv-research/bbndk-tools/host_10_3_1_12/win32/x86/usr/bin/blackberry-connect
KEY=/tmp/bb_key.pub
LOG=/tmp/bb_connect.log

# Run detached — MUST stay running for the tunnel to persist
nohup "$BC_BIN" 169.254.0.1 -password <DEVICE_PASSWORD> -sshPublicKey "$KEY" \
  > /tmp/bb_connect.log 2>&1 &
disown
```

**Wait 15–20 seconds** for:
1. Authentication over 4455
2. SSH public key transfer
4. `btool` to restart sshd (port 22 opens)

### Step 4: Verify Connection Log
```bash
cat /tmp/bb_connect.log
```
**Expected successful output:**
```
Info: Connecting to target 169.254.0.1:4455
Info: Authenticating with target 169.254.0.1:4455
Info: Encryption parameters verified
Info: Authenticating with target credentials.
Info: Successfully authenticated with target credentials.
Info: Sending ssh key to target 169.254.0.1:4455
Info: ssh key successfully transferred.
Info: Successfully connected. This application must remain running in order to use debug tools. Exiting the application will terminate this connection.
```

### Step 5: Verify Port 22 Open & Tunnel Alive
```bash
# Check port 22
timeout 5 bash -c 'echo > /dev/tcp/169.254.0.1/22' && echo "22 OPEN" || echo "22 closed"

# Verify tunnel process alive
pgrep -af Connect.jar
# Should show: java -Xmx512M -jar .../Connect.jar 169.254.0.1 -password <DEVICE_PASSWORD> -sshPublicKey /tmp/bb_key.pub
```

### Step 6: SSH as `devuser` with the Fresh Private Key
> **Paramiko configuration required:** QNX sshd only accepts RSA-SHA1 signatures. Newer paramiko defaults to SHA2 which must be disabled.

```bash
# Using the helper script (BBKEY env var points to fresh private key)
BBKEY=/tmp/bb_key python3 ~/bb-repo/connect_now.py
```
**Expected output:**
```
SSH CONNECTED!
CONNECTED
QNX BLACKBERRY-528E 8.0.0 2018/02/21-10:54:19EST MSM8960_V3.2.1.1_N_CLASSICNA_Rev:11 armle
```

---

## 5. Post-Connection Verification

Once SSH is established, verify the device state:
```bash
# Run via SSH (replace with your connect_now.py call pattern)
BBKEY=/tmp/bb_key python3 -c "
import paramiko, paramiko.transport as P, os
_orig = paramiko.transport.Transport.__init__
def _new(self, *a, **kw):
    kw.setdefault('server_sig_algs', False)
    return _orig(self, *a, **kw)
paramiko.transport.Transport.__init__ = _new
key = paramiko.RSAKey.from_private_key_file('/tmp/bb_key')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('169.254.0.1', 22, username='devuser', pkey=key,
          disabled_algorithms={'pubkeys':['rsa-sha2-512','rsa-sha2-256']},
          timeout=30, auth_timeout=120, banner_timeout=30, allow_agent=False, look_for_keys=False)
for cmd in ['id', 'ls -la /base/bin/__root', 'ls -la /proc/boot/pathtrust', 'uname -a']:
    _,o,_ = c.exec_command(cmd, timeout=10)
    print('>>>', cmd); print(o.read().decode(errors='replace'))
c.close()
"
```

**Expected:**
- `id` → `uid=100(devuser) gid=100(devuser) groups=...`
- `/base/bin/__root` → `-rwsrwsrwx 1 root nto 4488 ...` (setuid root helper present)
- `/proc/boot/pathtrust` → `-rwxr-x--- 1 root nto 9216 ...` (pathtrust binary present)

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `blackberry-connect`: "Error receiving data" / "Connection timed out" | qconnDoor not ready, stale `Connect.jar`, or device state | `pkill -f Connect.jar`, wait 5s, verify 4455 OPEN, retry. |
| `blackberry-connect`: "Provided ssh key is too small (4096-bit minimum)" | Key < 4096 bits | `ssh-keygen -t rsa -b 4096 -f /tmp/bb_key -N "" -q` |
| SSH: "Authentication failed" | Reused old key, wrong key, or SHA2 algos not disabled | Generate **fresh 4096-bit key**, ensure paramiko disables `rsa-sha2-512` and `rsa-sha2-256`. |
| Port 22 stays closed after `blackberry-connect` | `btool` didn't trigger, qconnDoor not authenticating | `pkill -f Connect.jar`, verify 4455 OPEN, fresh key, retry. |
| SSH works but `__root` gives "Operation not permitted" | `btool` hasn't whitelisted `__root` | On pre-rooted autoloaders, `btool` must contain `/proc/boot/pathtrust !/base/bin/__root`. If missing, the autoloader build lacks the pathtrust line. |
| `blackberry-connect` fails immediately | Java not found or wrong version | `java -version` must show 17+. Ensure `JAVA_HOME` not pointing to old JVM. |

---

## 7. Every-Session Checklist

- [ ] Device on USB, Dev Mode ON, password `<DEVICE_PASSWORD>` set in Settings → Security and Privacy → Development Mode
- [ ] `ping 169.254.0.1` OK
- [ ] Ports: `4455 OPEN`, `22 CLOSED`, `5555 OPEN`
- [ ] Fresh 4096-bit key generated (`ssh-keygen -t rsa -b 4096 -f /tmp/bb_key -N "" -q`)
- [ ] `blackberry-connect` started detached, log shows "Successfully connected"
- [ ] Wait 15–20s, verify `22 OPEN`
- [ ] `Connect.jar` process alive (`pgrep -af Connect.jar`)
- [ ] SSH with paramiko (SHA2 disabled) as `devuser` with fresh private key
- [ ] **Keep `blackberry-connect` running** — if it dies, tunnel drops and SSH closes

---

## 8. Files in This Repo

| File | Purpose |
|------|---------|
| `connect_now.py` | Paramiko SSH client with required QNX compatibility patches (loads `BBKEY` env var) |
| `reconnect.py` | Full automation: `blackberry-connect` + key push + SSH verify |
| `connect_win.py` | Windows PowerShell equivalent (reference) |
| `docs/ssh-connection-linux.md` | This document |

---

## 9. Security Notes

- **Private keys are live credentials** — never commit them. Add `*.pem`, `id_rsa*`, `bb_key*` to `.gitignore`.
- The `blackberry-connect` tunnel is unencrypted on the USB/RNDIS link — acceptable for local development.
- The `__root` helper (`/base/bin/__root`, setuid root) is present on pre-rooted autoloaders but **only works if `btool` whitelisted it** via `/proc/boot/pathtrust !/base/bin/__root`. If `__root` returns "Operation not permitted", the autoloader build lacks the whitelist line.
- **Do not use `root` login** — `sshd_config` allows it but the key is provisioned to `devuser` only.

---

## 9. Quick One-Liners for Daily Use

```bash
# Quick state check
ping -c1 169.254.0.1 && \
timeout 2 bash -c 'echo > /dev/tcp/169.254.0.1/4455' && echo "4455 OK" || echo "4455 DOWN"
timeout 2 bash -c 'echo > /dev/tcp/169.254.0.1/22' && echo "22 OK" || echo "22 DOWN"

# Full fresh connection (copy-paste)
KEY=$(mktemp /tmp/bb_key.XXXXXX)
ssh-keygen -t rsa -b 4096 -f "$KEY" -N "" -q
nohup $HOME/priv-research/bbndk-tools/host_10_3_1_12/win32/x86/usr/bin/blackberry-connect \
  169.254.0.1 -password <DEVICE_PASSWORD> -sshPublicKey "${KEY}.pub" > /tmp/bb.log 2>&1 &
sleep 20 && cat /tmp/bb.log
BBKEY="$KEY" python3 ~/bb-repo/connect_now.py
```

---

## 10. References

- **BlackBerry 10 NDK / `blackberry-connect`**: `archive.org/details/bbdevtools` → `bbndk.win32.tools.10.3.1.12.zip`
- **Paramiko QNX compatibility**: Disable `rsa-sha2-512` / `rsa-sha2-256`, set `server_sig_algs=False`
- **Device IP**: Always `169.254.0.1` on USB/RNDIS; host gets `169.254.0.2/30`
- **Device password**: `<DEVICE_PASSWORD>` (set in Settings → Security and Privacy → Development Mode; same as device lock password)

---

*Last verified: 2026-09-06 on ParrotOS Security Edition (OpenJDK 25), BlackBerry Classic SQC100 (BB10 10.3.3, Build `MSM8960_V3.2.1.1_N_CLASSICNA_Rev:11`), Device password `<DEVICE_PASSWORD>`.*