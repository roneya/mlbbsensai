"""
Full hero data update pipeline.

Runs in order:
  1. fetch_hero_matchups.py  → api_matchups.json
  2. build_hero_data.py      → hero_info.json
  3. patch_hero_data.py      → hero_info.json (adds relations + win rates)
"""

import subprocess
import sys
import time

SCRIPTS = [
    ("fetch_hero_matchups.py", "Fetching raw hero data from MLBB API"),
    ("build_hero_data.py",     "Building hero_info.json"),
    ("patch_hero_data.py",     "Patching relations and win rates"),
]

def run(script, label):
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    start = time.time()
    result = subprocess.run([sys.executable, script], capture_output=False)
    elapsed = time.time() - start
    if result.returncode != 0:
        print(f"\n[FAILED] {script} exited with code {result.returncode}")
        sys.exit(result.returncode)
    print(f"\n[DONE] {script} ({elapsed:.1f}s)")

if __name__ == "__main__":
    total_start = time.time()
    for script, label in SCRIPTS:
        run(script, label)
    print(f"\nAll done! hero_info.json is up to date. ({time.time() - total_start:.1f}s total)")
