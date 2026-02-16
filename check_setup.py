#!/usr/bin/env python3
"""
check_setup.py — Verify that all prerequisites are installed and configured.

Run this before anything else to make sure your environment is ready.
Checks Docker, MongoDB connectivity, Python dependencies, API key, and
the spreadsheet file.

Usage:
    python check_setup.py

Exit codes:
    0 = Everything looks good
    1 = One or more checks failed (see output for details)
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def check(name: str, condition: bool, fix: str = "") -> bool:
    """Print a check result and return whether it passed."""
    icon = "\u2705" if condition else "\u274c"
    print(f"  {icon} {name}")
    if not condition and fix:
        print(f"     Fix: {fix}")
    return condition


def main() -> None:
    print("\n" + "=" * 50)
    print("  ENVIRONMENT CHECK — Buddhist Dhammas Project")
    print("=" * 50 + "\n")

    all_ok = True

    # --- 1. Python version ---
    py_version = sys.version_info
    all_ok &= check(
        f"Python {py_version.major}.{py_version.minor}.{py_version.micro}",
        py_version >= (3, 8),
        "Python 3.8+ required. Install from python.org",
    )

    # --- 2. Docker installed ---
    docker_found = shutil.which("docker") is not None
    all_ok &= check(
        "Docker installed",
        docker_found,
        "Install Docker Desktop: https://docs.docker.com/get-docker/",
    )

    # --- 3. Docker Compose available ---
    compose_found = False
    if docker_found:
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            compose_found = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    all_ok &= check(
        "Docker Compose available",
        compose_found,
        "Docker Compose is included with Docker Desktop",
    )

    # --- 4. MongoDB connectivity ---
    mongo_ok = False
    try:
        from pymongo import MongoClient

        client = MongoClient(
            os.getenv("MONGO_URI", "mongodb://localhost:27017"),
            serverSelectionTimeoutMS=3000,
        )
        client.admin.command("ping")
        mongo_ok = True
        client.close()
    except Exception:
        pass
    all_ok &= check(
        "MongoDB reachable (localhost:27017)",
        mongo_ok,
        "Start MongoDB: docker compose up -d",
    )

    # --- 5. Python dependencies ---
    deps = {
        "pymongo": "pymongo",
        "openpyxl": "openpyxl",
        "pandas": "pandas",
        "anthropic": "anthropic",
    }
    for import_name, pip_name in deps.items():
        try:
            __import__(import_name)
            dep_ok = True
        except ImportError:
            dep_ok = False
        all_ok &= check(
            f"Python package: {import_name}",
            dep_ok,
            f"pip install {pip_name}",
        )

    # --- 6. Spreadsheet file ---
    spreadsheet = Path(__file__).parent / "buddhist_list_bud_content_v1.xlsx"
    all_ok &= check(
        "Spreadsheet found",
        spreadsheet.exists(),
        f"Expected at: {spreadsheet}",
    )

    # --- 7. Data directory ---
    data_dir = Path(__file__).parent / "data" / "essays"
    all_ok &= check(
        "Essays directory exists",
        data_dir.exists(),
        f"Create it: mkdir -p {data_dir}",
    )

    # --- 8. Anthropic API key (optional — only needed for essay generation) ---
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    has_key = api_key.startswith("sk-ant-")
    check(
        "ANTHROPIC_API_KEY set",
        has_key,
        "Optional — only needed for generate_essays.py. "
        "Set via: export ANTHROPIC_API_KEY=sk-ant-...",
    )
    # Don't fail overall for missing API key (it's optional)

    # --- Summary ---
    print(f"\n{'=' * 50}")
    if all_ok:
        print("  ALL CHECKS PASSED — Ready to go!")
        print("\n  Next steps:")
        print("    1. python generate_essays.py  # Generate essays (optional)")
        print("    2. python seed_db.py          # Seed the database")
        print("    3. python validate_db.py      # Verify integrity")
        print("    4. python query_examples.py   # Explore the graph")
    else:
        print("  SOME CHECKS FAILED — Fix the issues above first.")
    print("=" * 50 + "\n")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
