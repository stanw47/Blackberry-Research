================================================================================
SESSION 7B - QSEECOM-REACHABLE DAEMON AUDIT (option #2) - 2026-08-29
================================================================================
Goal: find a shell/untrusted_app-reachable daemon that can open /dev/qseecom and
has an auditable binder surface, to build the missing "prior foothold" for the
widevine trustlet chain (session 6F) or a direct QSEE path.

RESULTS (3 findings, one is a plan-changing gate):

[1] QSEECOM-CAPABLE DOMAINS (SELinux, enumerated from sepolicy_aaw068.bin)
  Parser: priv-research/sepolicy/parse_policy_tee.py (+ /tmp/opencode/sepolicy_tee.py)
  24 domains have tee_device:chr_file rules (the ONLY ones that can open /dev/qseecom):
    system_server, mfg_security, mfg_nvram, tee, drmserver, keystore, wfdservice,
    mcStarter, seempd, tbaseLoader, secotad, qseeproxy, init, qfp-daemon,
    mediaserver, seemp_health_daemon, gatekeeperd, mdtpdaemon, vtnvfsd,
    surfaceflinger, fidodaemon, vold, mfg_widevine, mfg_customization
  (perm grant is ioctl|read|create|setattr|relabelto|execmod - "open" bit
   ambiguous due to policy's 1-indexed perm table, but these are the intended
   QSEE clients. /dev/qseecom ueventd: 0660 system drmrpc.)

[2] vend_fidodaemon = Qualcomm QSEEConnectorService - AUDITED, HARDENED
  Binary: qscan/bins/vend_fidodaemon (aarch64, 38KB). Service name
  "com.qualcomm.qti.auth.fidocryptodaemon" (class android::QSEEConnectorService,
  interface android::IQSEEConnectorService).
  onTransact @ 0x4054 handles 3 codes:
    CODE 1 (load)        -> readStrongBinder(cb) + fcn.00003ee8 -> QSEECom_start_app (0x4668)
    CODE 2 (sendCommand) -> 3x readInt32 + operator new + readInplace -> vtable+0x28 -> fcn.00004958
    CODE 3 (unload)      -> readInt32 -> QSEECom_shutdown_app (0x4d58)
  sendCommand (0x4958) IS HARDENED:
    - bounds check: cmp (reqSize+rspSize), [this+0x28]  -> "Bad cmdLen/rspLen"
    - 64-byte alignment checks on req and rsp ("Command buffer not aligned")
    - QSEECom_send_cmd(handle, cmd_buf, reqSize, rsp_buf, rspSize)
    => CAF overflow fix present. No trivial overflow. load() = fixed app name,
       callback linkToDeath; no attacker-controlled string.

[3] CRITICAL GATE - BINDER REACHABILITY (this changes the plan)
  From avtab (binder class call / service_manager find):
  - shell         binder CALL: { keystore, surfaceflinger }        ONLY
  - untrusted_app binder CALL: { keystore, dataminer }             ONLY
  - fidodaemon binder callable by: { system_app, platform_app, servicemanager }
  - shell/untrusted_app have NO binder rule to fidodaemon, drmserver,
    mediaserver, qseeproxy (or any of the other 24 qseecom daemons).
  - shell service_manager: FIND only "servicemanager"; ADD fidodaemon_service
    and qseeproxy_service (register, not use).
  => The "audit fidodaemon/drmserver for a shell-reachable bug" path is CLOSED:
     shell cannot transact with those daemons at all. The trustlet delivery
     prerequisite is even harder than assumed: need platform_app/system_app-
     context first, OR a bug in a service shell CAN reach.

CORRECTED TARGET - KEYSTORE (and secondarily surfaceflinger):
  keystore is the INTERSECTION of (qseecom-capable) AND (shell+untrusted_app
  binder-reachable). It is the correct audit target.
  - Binary: qscan/bins/keystore (aarch64, 125KB, stripped) = standard AOSP
    keystore daemon (Android 6.0.1, Mar-2018 BB build).
  - keystore opens /dev/qseecom (uid system, drmrpc group) to use the QSEE
    keymaster TA. A keystore memory bug from shell == code exec in a
    qseecom-capable context (exactly the foothold needed).
  - Historical keystore CVEs to check patch status for (3.10 / 6.0.1):
    CVE-2016-2431/2432 (keyblob), CVE-2017-13246 (binder buffer), CVE-2015-6619,
    and the 'delete'/'get' entry enumeration races.
  - surfaceflinger (shell-reachable, qseecom-capable) = secondary; wfdservice/
    qfp-daemon are NOT shell-reachable (not in shell's binder set).
  - 'dataminer' (untrusted_app-reachable) = UNKNOWN BB-specific service, not a
    qseecom domain. Worth identifying but not the qseecom foothold.

NEXT STEPS (ranked):
  1. Audit keystore onTransact + keyblob/entry parsing for a shell-reachable
     bug (the real option #2). Binder surface is large (get/insert/delete/
     list/import/generate/verify + operation callbacks via BnKeystoreService).
  2. Check CVE-2016-2431/2432, CVE-2017-13246, CVE-2015-6619 patch status in
     this 2018 build (strings/behavior).
  3. Confirm live: `service list | grep keystore` + which uid shell uses to
     reach keystore (u:r:shell:s0 can call keystore binder per policy).
  4. Identify 'dataminer' service (untrusted_app-reachable, non-qseecom).

------------------------------------------------------------------------------
SESSION 7B (cont) - KEYSTORE RE - INITIAL MAP (2026-08-29)
------------------------------------------------------------------------------
Binaries (extracted from system.raw /lib64 via debugfs):
  - keystore (aarch64, 125KB) = KeyStore logic (blob I/O, keymaster HAL glue)
  - libkeystore_binder.so (aarch64, 71KB) = BnKeystoreService::onTransact
  - libkeystore-engine.so, libkeymaster1.so, libkeymaster_messages.so,
    libsoftkeymaster{,device}.so
  Interface descriptor: "android.security.keystore" (IKeystoreService).
  BnKeystoreService::onTransact @ 0x91dc (libkeystore_binder.so, 5412B switch).

HARDENING ALREADY OBSERVED (all the classic string-overflow fixes present):
  - getKeyNameForUid / encode-key-for-uid uses android::String8::format("%u_%s")
    (asprintf-backed) NOT sprintf into a fixed buffer => that overflow is fixed.
    ("%u_%s" @0x18730, used in fcn.0000a710.)
  - asprintf (not sprintf) imported; __memcpy_chk (FORTIFY_SOURCE) present.
  - "Provided blob length too large" length check present in 4 write-path
    functions (fcn 0xafdc/0xc1f0/0xe6e8/0x116dc) => write-side blob validation.

REMAINING AUDIT SURFACE (not yet audited):
  - onTransact switch: map exact transaction codes -> handlers. Prime targets:
    get(1), insert(2), generate(11: KeystoreArg[] count = integer-overflow
    candidate), import(12), sign(13), get_pubkey(15), addAuthToken.
  - KeystoreArg (Vector<sp<KeystoreArg>>) parcel read: count/len arithmetic.
  - Blob::readBlob on-disk keyblob length handling (read path, not write path).
  - CVE-2017-13246 (Jan-2018 keystore EoP) patch status - build declares
    2017-10-05 security level, so Jan-2018 fixes may be MISSING.

KEY TAKEAWAY: keystore is FORTIFY'd and string-safe, so the target is the
  integer-arithmetic / count-overflow class in the blob and KeystoreArg parse
  paths, not classic sprintf/strcpy. This is a real but multi-session audit.
================================================================================
