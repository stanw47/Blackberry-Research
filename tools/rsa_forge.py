import argparse
import hashlib
import math
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from Crypto.Util.number import long_to_bytes, bytes_to_long

def emsa_pkcs1_v1_5_encode(message: bytes, emlen: int, is_hash: bool = False) -> bytes:
    """Construct EMSA-PKCS1-v1_5 encoding."""
    if is_hash:
        digest = message
    else:
        digest = hashlib.sha1(message).digest()
    digest_info_prefix = bytes.fromhex("3021300906052b0e03021a05000414")  # ASN.1 for SHA-1
    t = digest_info_prefix + digest
    if emlen < len(t) + 11:
        raise ValueError("Intended encoded message length too short")
    ps = b"\xff" * (emlen - len(t) - 3)
    return b"\x00\x01" + ps + b"\x00" + t

def integer_nth_root(x: int, n: int) -> int:
    """Find the integer component of the n'th root of x."""
    high = 1
    while high ** n <= x:
        high *= 2
    low = high // 2
    while low < high:
        mid = (low + high) // 2
        if mid ** n < x:
            low = mid + 1
        else:
            high = mid
    return low if low ** n == x else low - 1

def forge_signature_e3(encoded: bytes) -> Optional[int]:
    """Forge signature directly for e=3 via integer cube root."""
    em_int = bytes_to_long(encoded)
    s = integer_nth_root(em_int, 3)
    if pow(s, 3) == em_int:
        return s
    return None

def forge_signature_bruteforce(e: int, n: int, encoded: bytes, threads: int = 1) -> Optional[int]:
    """Forge signature using brute-force search for e > 3."""
    target = bytes_to_long(encoded)
    lock = threading.Lock()
    result = [None]

    def search(start: int, step: int):
        x = start
        while result[0] is None:
            if pow(x, e, n) == target:
                with lock:
                    result[0] = x
                break
            x += step

    with ThreadPoolExecutor(max_workers=threads) as executor:
        for i in range(threads):
            executor.submit(search, i, threads)
    return result[0]

def main():
    parser = argparse.ArgumentParser(description="Forge RSA PKCS#1 v1.5 Signature")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--msg", help="Message to sign")
    group.add_argument("--hash", help="SHA1 hash (hex) of the message")
    group.add_argument("--msg-file", help="Read message to sign from file")
    group.add_argument("--msg-hex", help="Message as hex string")
    parser.add_argument("--n", required=True, help="Modulus (hex)")
    parser.add_argument("--e", type=int, required=True, help="Public exponent")
    parser.add_argument("--threads", type=int, default=4, help="Threads (for e > 3)")
    args = parser.parse_args()

    if args.hash:
        msg = bytes.fromhex(args.hash)
        is_hash = True
    elif args.msg_file:
        with open(args.msg_file, 'rb') as f:
            msg = f.read()
        is_hash = False
    elif args.msg_hex:
        msg = bytes.fromhex(args.msg_hex)
        is_hash = False
    else:
        msg = args.msg.encode()
        is_hash = False

    n = int(args.n, 16)
    e = args.e
    emlen = (n.bit_length() + 7) // 8
    encoded = emsa_pkcs1_v1_5_encode(msg, emlen, is_hash)

    if e == 3:
        sig = forge_signature_e3(encoded)
    else:
        sig = forge_signature_bruteforce(e, n, encoded, threads=args.threads)

    if sig:
        print("Forged signature:")
        print(long_to_bytes(sig).hex())
    else:
        print("Failed to forge signature")

if __name__ == "__main__":
    main()
