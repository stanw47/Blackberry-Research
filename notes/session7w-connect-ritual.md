================================================================================
SESSION 7W - SSH CONNECTION RITUAL: KEY REQUIRED EVERY SESSION
================================================================================
2026-09-02. Captures the REQUIRED reconnection procedure and current state.

[0] THE ONE-LINE RULE (READ THIS FIRST)
  Every single session, you MUST connect over SSH using the RSA key located at
  `id_rsa` (public half: `id_rsa.pub`). There is no password-only path and no
  session reuse. Treat every session as a fresh connect:
    python3 connect_now.py
  `connect_now.py` loads `id_rsa`, connects to 169.254.0.1:22 as `devuser`,
  and requires two paramiko settings that the stock client does not use by
  default:
    1. server_sig_algs=False  (patched via monkeypatch of Transport.__init__)
    2. disabled_algorithms={'pubkeys':['rsa-sha2-512','rsa-sha2-256']}
  (The QNX sshd only accepts RSA-SHA1 signatures, so the newer SHA2 host-key
   algorithms must be disabled or the handshake is refused.)

[1] WHERE THE KEY COMES FROM
  - The private key is provisioned ONCE against the device (the device's
    authorized_keys is installed from `id_rsa.pub`). It lives at:
        /home/stanw47/Documents/blackberry-research/id_rsa
  - `reconnect.py` documents the original provisioning path: run the Host SDK
    `blackberry-connect` tool with `-sshPublicKey <id_rsa.pub>` to push the key
    onto the device and establish the USB/tunnel link. NOTE: on the Parrot
    Linux box (no wine, no new-privileges/root), the win32 `blackberry-connect`
    binary is NOT runnable; the practical path is that the device keeps the
    provisioned key and we use `connect_now.py` to re-establish.

[2] WHY "CONNECTION REFUSED" HAPPENS
  `connect_now.py` will FAIL with:
      [Errno None] Unable to connect to port 22 on 169.254.0.1
  whenever the device's sshd is not LISTENING on port 22. This is a NETWORK/
  DAEMON state, not a key problem. Verified live (2026-09-02):
      ping 169.254.0.1                      -> OK (device reachable)
      /dev/tcp/169.254.0.1/22               -> REFUSED (no SSH listener)
      /dev/tcp/169.254.0.1/5555             -> OPEN (adbd only, offline/unauthed)
  So the reconnection recipe is:
    a) confirm port 22 is listening on the device (if not, get sshd started);
    b) run `python3 connect_now.py` (or the in-tree SSH helper) with the key.
  The key alone is useless until a listener exists; the listener alone is
  useless until the key is presented. Both must hold.

[3] QR (QUICK REFERENCE) - EVERY NEW SESSION
  1. Verify the link:   ping -c1 -W2 169.254.0.1
  2. Verify listener:   echo > /dev/tcp/169.254.0.1/22  (must not error)
  3. Connect with key: python3 connect_now.py   -> expect "SSH CONNECTED!"
  If step 2 fails, the phone's sshd is down; establish it (restart sshd or
  replug/push key) before step 3.

[3b] KEY RE-PUSH AFTER EVERY REBOOT / DEV-MODE RE-ENABLE  (2026-09-02, verified)
  After the phone reboots and Development Mode is toggled back on, the
  device's authorized_keys NO LONGER contains our public key. sshd listens
  (port 22 OPEN) but auth fails ("Authentication failed"). You MUST re-push the
  key before paramiko will work:
      BC=.../bbndk-tools/host_10_3_1_12/win32/x86/usr/bin/blackberry-connect
      # RUN IN BACKGROUND - it is the SSH tunnel and dies on process exit:
      nohup "$BC" 169.254.0.1 -password <DEV_PW> \
            -sshPublicKey /home/stanw47/Documents/blackberry-research/id_rsa.pub \
            > /tmp/opencode/bb_connect.log 2>&1 &
      sleep 6   # wait for auth+key transfer
      python3 connect_now.py
  blackberry-connect auths to the device on TCP port 4455, pushes id_rsa.pub,
  and establishes the tunnel. It is a `java -jar Connect.jar` wrapper (needs
  Java, NOT wine). It MUST stay running for the session to persist.

[4] SECURITY NOTE ON THE KEY
  `id_rsa` is a live credential granting shell access to the device. It MUST
  stay out of the git repository. If `id_rsa`/`id_rsa.pub` ever appear as
  untracked in `git status`, add them to `.gitignore` (see repo .gitignore)
  and do NOT `git add` them.