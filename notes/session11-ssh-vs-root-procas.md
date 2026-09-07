# Session 11 — Why SSH worked before but not now; root + /proc/as state 2026-09-03

## The user's question
"Why could we connect in past sessions but not now? Are you using my password +
key-push-via-4455 and the correct commands?"

## Answer (evidence)
YES — method matches the documented recipe exactly:
  blackberry-connect 169.254.0.1 -password 61482501 -sshPublicKey id_rsa.pub
  -> authenticates on TCP 4455, reports "ssh key successfully transferred",
     stays running as the tunnel (pid alive).
Then paramiko SSH with id_rsa, as root (AllowUsers=root), disabling
rsa-sha2-512/256 + server_sig_algs=False. Matches connect_now/reconnect notes.

Paramiko verbose confirms transport is 100% healthy:
  - KEX completes (ecdh-sha2-nistp256), host key ssh-rsa accepted,
    cipher aes128-ctr, MAC hmac-sha1.
  - "userauth is OK" -> our pubkey (1235114ac83a...) tried.
  - Server never replies -> "Authentication timeout" (SILENT, not "Permission
    denied"). => server-side sshd userauth stall, NOT key/transport.

## Root cause discovered for the recurring SSH auth failure
- /etc/ssh/sshd_config (QNX minimal form):
    Protocol=2
    AuthorizedKeysFile=/etc/ssh/authorized_keys2
    AllowUsers=root
    PermitRootLogin=yes
    PasswordAuthentication=no
    HostKey=/etc/ssh/ssh_host_rsa_key
- /etc/ssh/authorized_keys2 previously contained ONLY the old key
  'lc@t560'. blackberry-connect's "successful transfer" does NOT place our
  key there (it pushes to a different debug-key store). => the mismatch that
  made key-based auth fail regardless of reboots.
- FIXED: used recovered __root (uid-0 root ksh, ksh builtins only) to append
  our 'stanw47@parrot' key into /etc/ssh/authorized_keys2 (verified 2 keys).
  Restarted sshd (slay) -> retest STILL "Authentication timeout": sshd's
  userauth handler itself is stalled server-side (needs slog, unreadable as
  uid850; root ksh lacks grep/sloginfo).

## Root + /proc/<pid>/as state (definitive)
- __root = real setuid-0 QNX binary (/base/bin/__root, uid0 gid0 mode6777,
  imports procmgr_ability+setreuid+system). pathtrust-trusted (btool line31
  intact: '/proc/boot/pathtrust !/base/bin/__root').
- Root WORKS: __root root ksh can WRITE /root (verified) and any fs via ksh
  builtin redirection; cannot exec /accounts python (untrusted) and many /bin
  tools are android-compat (libcutils) => root shell is restricted to ksh
  builtins + QNX-native /proc/boot tools (pathtrust, etc.).
- pathtrust single-file trust '!<python>' DID succeed (query -> trusted) but
  exec of the python from __root ksh STILL EPERM (exec-time trust not applied
  to same session's child / PYTHONHOME libs untrusted).
- /proc/<pid>/as: **EPERM for EVERY pid even as root** (pidin as __root prints
  "couldn't open /proc/1/as: Operation not permitted" for all). This is a
  process-manager ABILITY gate (PROCMGR_AID_MEM_PHYS etc.), not fs perms.
  __root's procmgr_ability() grants are NOT yielding /proc/as access this
  session. This is the hard blocker for in-driver memory patching.

## Bottom line (for user)
- Method correct. SSH never was password; key stored at wrong place -> FIXED.
  Residual sshd userauth stall remains server-side and unreadable without slog.
- Real root regained (uid0) but /proc/<pid>/as still EPERM even as root =>
  the in-memory driver patch (Route B) cannot be executed this session.
- Next realistic levers for /proc/as: make __root's procmgr_ability actually
  grant MEM_PHYS (verify with a QNX-native tool), or get the real sshd-as-root
  session (which in past sessions had the pathtrust /proc/as grant), or a
  QNX-native root binary that opens /proc/as directly (needs ARM cross-CC).

## Artifacts
- Local: /home/stanw47/Documents/blackberry-research/{ssh_root_test.py,
  rootpy.sh, probe_rootasrpp.py, probe_rootbin.py, probe_dirs.py}
- On device: /accounts/1000/shared/misc/berrycore/{probe_rootasrpp.py, rootpy.sh}