#!/usr/bin/env python3
"""Test yt-dlp connectivity through the SOCKS5 proxy."""

import os
import subprocess
import sys

# Ensure deno is available for yt-dlp JS extraction
deno_bin = os.path.expanduser("~/.deno/bin")
if deno_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = deno_bin + ":" + os.environ["PATH"]

PROXY = "socks5://127.0.0.1:1080"
# Rick Astley - reliable, always-available YouTube video
TEST_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

def run(cmd, label):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode == 0:
        print(f"✅ {label}: PASSED")
    else:
        print(f"❌ {label}: FAILED (exit code {result.returncode})")
    return result.returncode

def main():
    # 1. Check yt-dlp is installed
    rc = run(["yt-dlp", "--version"], "yt-dlp version")
    if rc != 0:
        print("yt-dlp not found. Install with: pip install -U yt-dlp")
        sys.exit(1)

    # 2. Test WITHOUT proxy — just extract info (no download)
    print("\n\n>>> Testing WITHOUT proxy...")
    rc_no_proxy = run(
        ["yt-dlp", "--skip-download", "--print", "title", TEST_URL],
        "yt-dlp without proxy"
    )

    # 3. Test WITH proxy — just extract info (no download)
    print("\n\n>>> Testing WITH SOCKS5 proxy...")
    rc_proxy = run(
        ["yt-dlp", "--proxy", PROXY, "--skip-download", "--print", "title", TEST_URL],
        "yt-dlp with proxy"
    )

    # 4. Test proxy with a short download (audio only, smallest format)
    if rc_proxy == 0:
        print("\n\n>>> Testing download through proxy (smallest audio)...")
        rc_dl = run(
            [
                "yt-dlp", "--proxy", PROXY,
                "-f", "worst",
                "-o", "/tmp/ytdlp_test.%(ext)s",
                "--no-playlist",
                TEST_URL,
            ],
            "yt-dlp proxy download"
        )
        # Cleanup
        subprocess.run("rm -f /tmp/ytdlp_test.*", shell=True)

    # Summary
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    print(f"  Without proxy: {'✅ OK' if rc_no_proxy == 0 else '❌ FAILED'}")
    print(f"  With proxy:    {'✅ OK' if rc_proxy == 0 else '❌ FAILED'}")
    if rc_proxy == 0:
        print(f"  Download test: {'✅ OK' if rc_dl == 0 else '❌ FAILED'}")

if __name__ == "__main__":
    main()
