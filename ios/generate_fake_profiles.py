#!/usr/bin/env python3
"""Create self-signed build-only profiles for the native NagramiX bundle ID."""

from __future__ import annotations

import argparse
import base64
import os
import plistlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def run(*args: str, input_data: bytes | None = None) -> bytes:
    return subprocess.run(args, input=input_data, check=True, capture_output=True).stdout


def rewrite(value: Any, replacements: list[tuple[str, str]]) -> Any:
    if isinstance(value, str):
        for old, new in replacements:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [rewrite(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: rewrite(item, replacements) for key, item in value.items()}
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-profiles", type=Path, required=True)
    parser.add_argument("--source-certs", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--upstream-team", required=True)
    parser.add_argument("--upstream-bundle", required=True)
    parser.add_argument("--team", required=True)
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()

    destination = args.destination.resolve()
    profiles_destination = destination / "profiles"
    certs_destination = destination / "certs"
    shutil.rmtree(destination, ignore_errors=True)
    profiles_destination.mkdir(parents=True)
    shutil.copytree(args.source_certs, certs_destination)

    p12_path = certs_destination / "SelfSigned.p12"
    cert_pem = run(
        "openssl", "pkcs12", "-in", str(p12_path), "-passin", "pass:",
        "-nokeys", "-legacy"
    )
    cert_der = run("openssl", "x509", "-outform", "DER", input_data=cert_pem)
    subject = run(
        "openssl", "x509", "-noout", "-subject", "-nameopt", "oneline,-esc_msb",
        input_data=cert_pem
    ).decode().strip()
    if "CN = " not in subject:
        raise SystemExit("Could not resolve the fake signing identity")
    signing_identity = subject.split("CN = ")[-1].split(",")[0].strip()

    keychain = f"nagramix-{os.getpid()}.keychain"
    password = "nagramix-temp"
    run("security", "create-keychain", "-p", password, keychain)
    try:
        existing = run("security", "list-keychains", "-d", "user").decode().replace('"', '').split()
        run("security", "list-keychains", "-d", "user", "-s", keychain, *existing)
        run("security", "unlock-keychain", "-p", password, keychain)
        run("security", "import", str(p12_path), "-k", keychain, "-P", "", "-T", "/usr/bin/codesign", "-T", "/usr/bin/security")
        run("security", "set-key-partition-list", "-S", "apple-tool:,apple:", "-k", password, keychain)

        replacements = [
            (f"{args.upstream_team}.{args.upstream_bundle}", f"{args.team}.{args.bundle}"),
            (args.upstream_bundle, args.bundle),
            (args.upstream_team, args.team),
        ]
        count = 0
        for source in sorted(args.source_profiles.glob("*.mobileprovision")):
            decoded = run("security", "cms", "-D", "-i", str(source))
            profile = rewrite(plistlib.loads(decoded), replacements)
            profile["DeveloperCertificates"] = [cert_der]
            profile.pop("DER-Encoded-Profile", None)
            with tempfile.NamedTemporaryFile(suffix=".plist", delete=False) as temp:
                plistlib.dump(profile, temp, fmt=plistlib.FMT_XML, sort_keys=False)
                temp_path = temp.name
            try:
                run(
                    "security", "cms", "-S", "-k", keychain, "-N", signing_identity,
                    "-i", temp_path, "-o", str(profiles_destination / source.name)
                )
            finally:
                os.unlink(temp_path)
            count += 1
    finally:
        subprocess.run(["security", "delete-keychain", keychain], check=False, capture_output=True)

    if count == 0:
        raise SystemExit("No source provisioning profiles were found")
    print(f"Generated {count} build-only NagramiX profiles")


if __name__ == "__main__":
    main()
