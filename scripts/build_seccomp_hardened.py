#!/usr/bin/env python3
"""
Genere security/seccomp-hardened.json a partir du profil par defaut de Docker,
en retirant en plus une liste de syscalls dangereux (cahier des charges B.3/B.5).

Prerequis : security/seccomp-default.json doit deja exister, par exemple via :
    curl -L -o security/seccomp-default.json \\
        https://raw.githubusercontent.com/moby/moby/v25.0.0/profiles/seccomp/default.json

Usage:
    python3 scripts/build_seccomp_hardened.py
"""
import json

SRC = "security/seccomp-default.json"
DST = "security/seccomp-hardened.json"

# Syscalls supplementaires a bloquer par rapport au profil par defaut de Docker
# (debogage/traçage processus, montage, modules kernel, admin systeme, cles noyau, etc.)
EXTRA_BLOCKED = {
    "ptrace", "mount", "umount2", "umount", "reboot",
    "kexec_load", "kexec_file_load", "init_module", "finit_module",
    "delete_module", "create_module", "query_module", "get_kernel_syms",
    "nfsservctl", "acct", "add_key", "request_key", "keyctl",
    "swapon", "swapoff", "sethostname", "setdomainname",
    "iopl", "ioperm", "pivot_root", "settimeofday", "stime",
    "clock_settime", "clock_adjtime", "vm86", "vm86old", "uselib",
    "personality", "process_vm_readv", "process_vm_writev",
    "bpf", "perf_event_open",
}

def main():
    with open(SRC, "r", encoding="utf-8") as f:
        profile = json.load(f)

    removed_found = set()
    for entry in profile.get("syscalls", []):
        names = entry.get("names", [])
        kept = [n for n in names if n not in EXTRA_BLOCKED]
        removed_found.update(set(names) - set(kept))
        entry["names"] = kept

    profile["syscalls"] = [e for e in profile["syscalls"] if e.get("names")]

    with open(DST, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

    print(f"Profil durci ecrit dans {DST}")
    print(f"{len(removed_found)} syscall(s) effectivement retires du profil par defaut :")
    for n in sorted(removed_found):
        print(f"  - {n}")

if __name__ == "__main__":
    main()
