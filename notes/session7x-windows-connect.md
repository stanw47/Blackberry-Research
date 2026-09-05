================================================================================
SESSION 7X - WINDOWS SSH CONNECT: STATUS AND THE FULL WORKING RECIPE
================================================================================
2026-09-04. Records the FIRST successful SSH session to the Classic from the
Windows notebook (host: Stanley Williamson's Windows PC), including the key
re-push that was failing earlier today.

[0] CURRENT STATE (verified 2026-09-04)
  - Device: QNX BLACKBERRY-528E 8.0.0 MSM8960_V3.2.1.1_N_CLASSICNA (Classic).
  - Win machine has: BlackBerry Blend 1.2.0.50, BlackBerry Link 1.2.4.39,
    BlackBerry 10 Desktop Software, BlackBerry Device/Comm Drivers, Java 21.
  - SSH (port 22 on 169.254.0.1) is only available through a BlackBerry
    `blackberry-connect` tunnel that MUST stay running.
  - Working example (this session):
      python connect_now.py          # BBKEY env or edit path to the classic key
    => "SSH CONNECTED!"
  - Confirmed root via BerryCore dir (mode/readable):
      ls /accounts/1000/shared/misc/berrycore/VERSION => 0.88.0

[1] WHY SSH DIED EARLIER / WHAT WAS BLOCKING
  - `bbssh.ps1` connects as root with the old bb10_ssh_key; initially the
    device's sshd was NOT listening on 22 (only 4455 [dev auth], 5555 [adb],
    445 were open). That is the "banner exchange: Connection refused" seen in
    bbssh.ps1 / paramiko.
  - To start sshd you MUST run blackberry-connect (it is BOTH: pushes the pub
    key to the device AND is the SSH tunnel).
  - On the Parrot Linux box (no wine) that tool could not run; on Windows it
    runs fine and is the missing piece from the earlier session.

[2] THE WINDOWS RECIPE (proven 2026-09-04)
  1. Ensure device is in Development Mode (dev pw = 61482501) and over USB.
  2. Java needed (Java 21 worked).
  3. blackberry-connect = win32 host tool from BB10 NDK tools:
       ...\host_10_3_1_12\win32\x86\usr\bin\blackberry-connect(.bat)
     (downloaded: archive.org/details/bbdevtools -> bbndk.win32.tools.10.3.1.12.zip)
  4. Derive the public key from the private key if missing:
       ssh-keygen -y -f <id_rsa> > <id_rsa.pub>
     NOTE: pubkey line for blackberry-connect must NOT contain the trailing
     comment ("Invalid ssh key contents" otherwise): use a clean single-line
     `ssh-rsa AAAA...` without a comment.
  5. Run in background (tunnel stays alive):
       Start-Process cmd -ArgumentList '/c', "<bc> 169.254.0.1 -password 61482501
             -sshPublicKey <id_rsa.pub> > connect.log 2>&1" -WindowStyle Hidden
     Wait ~8s; then verify:  Test-NetConnection 169.254.0.1 -Port 22 -> True
  6. SSH as devuser, NOT root (key is provisioned to devuser only):
       python connect_now.py   (auth_timeout bumped to 120s; QNX sshd is SLOW
       at the auth stage - the earlier 20s auth_timeout caused
       "AuthenticationException: Authentication timeout").  root login FAILS
       with "Authentication failed" unless the key is also placed in root's
       authorized_keys.

[3] ENV / QUIRKS SEEN (2026-09-04)
  - Windows OpenSSH client (9.5p2) negotiated the full handshake then stalls
    at publickey with rsa-sha2 default; the ONLY reliable client is paramiko
    with server_sig_algs=False + disabled_algorithms rsa-sha2 (repo scripts).
  - paramiko 3.5.1 is fine; paramiko 5.x dropped 'ssh-rsa' entirely (breaks).

[4] NEXT STEPS / UNCLEANED
  - bb10_ssh_key (4096-bit RSA) is the working Windows key; pushes to devuser.
  - BerryCore v0.88.0 confirmed at /accounts/1000/shared/misc/berrycore/.
  - Bring this window's workflow (run_ssh.py wrapped) onto the repo.