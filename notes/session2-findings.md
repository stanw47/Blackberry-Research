# Priv STV100-1 — Session 2 Findings (flash surface map + crypto verdict)

## Conclusive
1. **boot.img is cryptographically verified vs bootsig at boot.**
   - Test: stock boot.img + FLIPPED last-byte sig -> `fastboot reboot` -> instantly back to fastboot (auth reject).
   - Stock restored, device healthy.
   - => Cannot just append any sig; need real BlackBerry signature or verification bypass.

2. **Flash surface is WIDE open (via BB custom fastboot, and Google fastboot for boot/sig):**
   - Allowed (authboot NOT required):
     - boot, recovery, bootsig, recoverysig
     - aboot, sbl1, tz, rpm, hyp, pmic, sdi  (signed images accepted, no gate)
     - modemst1, modemst2  (FULLY writable, no gate, no content check on 4KB test)
   - Denied (authboot required):
     - devinfo, bootselect, debug_token, gsign, keystore, crypto, metadata,
       carrier(erase-denied), rfcal, rfbackup, bcota, boot0hwi, phyboot1hwi,
       nvuser, perm, LOGO/spla, all arbitrary names

3. **oem commands: ONLY `oem info` and `oem securewipe` work unprivileged.**
   - `oem securewipe` works ONLY via BB custom fastboot client (Google client = denied/dropped)
   - securewipe = USER wipe mode, reboots device, WIPES boot/recovery sigs (HLOS "Not Present" until reflash)
   - Everything else (unlock/lock/factory-mode/gptinfo/read/... ) = authboot command permission denied

4. **Device security state (unchanged by wipe):**
   - Insecure: false, WP Type: permanent, security: enabled, bootchain: new
   - hlos_unsigned.tkn: disabled, hlos_signature.tkn: NONE, no debug tokens (perm/nvuser)
   - is-password-set: no
   - bootmode: PRODUCT_MODE, variant na, authboot_api_ver 1.3
   - Primary bootchain AAW068, Backup AAC603

5. **Boot verification flow (from aboot strings):**
   - "Authenticating boot image (N): start/failed/done return" 
   - "Device is unlocked! Skipping verification..." (unlock-state bypass EXISTS)
   - "Device is in factory mode continuing..." (factory mode continues on auth fail!)
   - "%s : (insecure) continue boot"
   - "Blocklist check disabled in Factory mode"
   - "SFI image booting disabled in factory mode"
   - "BOOT COUNT EXPIRED !!!!!"
   - "HLOS/bootchain blocked" (blocklist/antrollback)
   - "Failing boot due to NV Signature verification failure" vs "...proceeding with boot anyways"

6. **Two drastically different gating strings for NV signature:**
   - "NV Signature verification failed, proceeding with boot anyways"  (NON-fatal path!)
   - "Failing boot due to NV Signature verification failure" (fatal)

## Open attack vectors (next)
- A) FACTORY MODE bypass (disables RPMB + TZ listeners; auth-check continues boot).
  Entering = `oem set-factory-mode` (gated). BUT wipe path had "GRS wipe" (cmd_oem_grs_wipe).
  - "Failed to initialize factory mode on first boot" => factory init hooks during first boot.
- B) Unlock-state (is_unlocked) in devinfo; devinfo flash gated. GPT/phyboot rewrite may bypass.
- C) modemst1/2 writable => NV items may include fuse/secure-boot config or EDL-switch flag.
- D) Blocklist wipe (`oem blocklist-wipe`) un-gated? NOT tested yet! anti-rollback reset.
- E) Backup bootchain AAC603: booting the older/alt chain might have weaker checks.

## Remaining unknowns
- What EXACTLY is verified: RSA/ECDSA key, where key lives (aboot vs TZ).
- Whether "proceeding with boot anyways" fires under conditions we can reach.
