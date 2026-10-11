# Cross-device: BlackBerry Mux auth protocol (Priv AAW068 / DTEK era)

The Priv-era (and DTEK-era) bootloader auth transport. Differs from the
KEYone's pcauthtool protocol (cookie `0xbba78701`, `Blackberry-KeyOne-Research/notes/59-60`):
the constant does not exist anywhere in the Priv image, and the Priv instead
ships the **Mux** layer.

Source of this map: static analysis of `emmc_appsboot.mbn` (AAW068) -
`Blackberry-Priv-Research/notes/session5-canary-and-nvsig.md` and
`session3-authfull-decode.md`. All addresses virtual (base 0xf900000).

## Layering

```
pcauthtool/bbauthtoold (host tool, leaks from AAO.zip autoloader)
        |
   USB bulk (fastboot PID 0fca:8030; bbauthd bridged via 0fca:8032 in Android)
        |
  usb_mux (bbry/app/bbmux/mux.c)
        |
   Mux channels: Control Channel + registered channels:
     AUTHBOOT-venice{apac,att,emea,vzw,na,sprint}
     NVSIG-venice{...}   DBGSIG-venice{...}
     DDT-venice{...}     STP-venice{...}
        |
   RTAS ops:  rtas_init_tool_authorization / challenge create /
              verify response / nv_sig verify (the overflow)
        |
   permission gate FUN_0f9351f4 (types 0..10 -> RTAS mux codes 0x1000..0x1008)
```

## Key symbols / strings (AAW068)

| VA | String / meaning |
|---|---|
| 0xf9cfcb8 | `controlPacketReceived` |
| 0xf9cfcd0 | `rtas_init_tool_authorization` |
| 0xf9cfcf0 | `sendNextPacket` |
| 0xf9d0108 | `usb_mux` |
| 0xf9d10a8 | `Control Channel` |
| 0xf9d1110/0xf9d1118 | `mux_rx` / `mux_tx` |
| 0xf9d11f0 | `requestEncryption` |
| 0xf9d1204 | `mux_msg_handler` |
| 0xf9d1214 | `rtas_cmd_authorization_check` |
| 0xf9d1234 | `MessageClient` |
| 0xf9d1244 | `createPasswordChallenge` |
| 0xf9d1284 | `MuxRedirectedPasswordChallenge` |
| 0xf9cfe24 | `Mux: %s: Host encryption version %d.%d not supported` |
| 0xf9cfe5c | `Mux: %s: Host does not support necessary encryption capabilities (%x)` |
| 0xf9d0b20 | `Mux: Max password attempts exceeded. Wiping device...` |
| 0xf9d0920 | `Mux: %s: Invalid tool name or name len!` |
| 0xf9d0cf4 | `Mux: Unknown control message: 0x%x` |
| 0xf9d0c88 | `Mux: %s: Authentication response len: %d, blob len: %d, sig len: %d` |
| 0xf9d0bec | `Mux: %s: Not enough data passed to authentication response. Expected %d got %d` |
| 0xf9d5c50 | `RTAS initialize context` |
| 0xf9d5cac/0xf9d5cc8/0xf9d5cec | `RTAS challenge requested` / `RTAS NV sig challenge requested` / `RTAS ddt challenge requested` |
| 0xf9d5d10 | `RTAS verify response` |
| 0xf9d5e18 | `RTAS verify NV sig response` |
| 0xf9d5e38 | `Could not find RTAS RSA key` |

Channel table at 0xf9d7480: entries of `{name, ~0x90-byte key blob}`:
`NVSIG-veniceapac/att/emea/vzw`, `AUTHBOOT-venicena/sprint/...`, `DBGSIG-*`,
`DDT-*`, `STP-*` (full list in session5 notes). The generic `NVSIG` record
at 0xf9d5a10 carries index `4294967295` and an ASN.1 OID
`1.3.6.1.4.1.2838.26` (0x30 21 30 09 06 05 2b 0e 03 02 1a 05 00 04 14 00).

## Control flow (reconstructed)

1. Host opens the Mux **Control Channel** and registers/opens a tool channel
   (e.g. `NVSIG-venice<carrier>`) via the control message dispatch
   (`mux_msg_handler`; unknown control messages are rejected).
2. Encryption negotiation (`requestEncryption`; version/capability
   handshake; mismatch -> "Host encryption version not supported").
3. Tool authorization (`rtas_init_tool_authorization`) -> work-level slots
   (0x170-byte entries at 0xfa79908; state byte at +0x70 must reach 6 before
   `rtas_cmd_authorization_check` passes -> this is the gate behind
   `oem set-factory-mode` etc.).
4. Challenge flow: `createPasswordChallenge` /
   `MuxRedirectedPasswordChallenge` (password challenge with attempt counter,
   wipe on exceed) and `RTAS [NV sig] challenge requested` -> the challenge
   builder (0xf9538f8 area: "Cannot fit challlenge in supplied buffer") asks
   TZ to encrypt pin/BSN records.
5. Response: `RTAS verify [NV sig] response` -> verifier 0xf953e68 (the
   overflow; see the catalog section 11) -> ECDSA verify 0xf965240.

## Exploit relevance

- The nv_sig response verifier is the same vulnerable shape as the KEYone's
  (notes/60), reachable over Mux once the NVSIG channel + challenge are
  established. The wire format of the control messages is not yet mapped;
  the fastest empirical route is a live fastboot session against 0fca:8030
  with the string map above for oracle feedback.
- Gate to profitability: the bootloader stack canary. See the catalog
  section 10 - the Priv's SCM-RNG failure path falls back to an **unseeded
  LCG** (`0xf971798`, state 0xfa63058, no seed write in the image ->
  deterministic from BSS zero). A live canary-ladder probe settles it.
