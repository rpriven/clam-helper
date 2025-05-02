# clam-helper.py

import os
import sys
import shutil
import datetime
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# === CONFIGURABLE ===
MAX_THREADS = 4
QUARANTINE_DIR = Path.home() / ".quarantine"
SCAN_LOG_BASE = Path.home() / ".clamscan_logs"
CRASH_LOG = SCAN_LOG_BASE / "crash_summary.txt"
EMPTY_LOG = SCAN_LOG_BASE / "empty_files.txt"
SUMMARY_LOG = SCAN_LOG_BASE / "summary.txt"
MAX_SCAN_SIZE_MB = 200  # Optional: set to None to omit
MAX_FILE_SIZE_MB = 100  # Optional: set to None to omit
CLAMSCAN_PATH = shutil.which("clamscan") or "/usr/bin/clamscan"

# === HELPERS ===


def sanitize_path(path: str) -> str:
    path = path.strip().strip('"').strip("'")
    path = path.replace('\\ ', ' ').replace('\\\\', '\\')
    return os.path.expanduser(os.path.normpath(path))


def log(message: str, log_file: Path):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")


def log_to(file_path, line):
    with open(file_path, "a") as f:
        f.write(line + "\n")


def scan_directory(target_dir: Path, quarantine: Path, log_dir: Path) -> Path:
    log_file = log_dir / f"scan_{target_dir.name}.log"
    crash_file = log_dir / "crash_summary.txt"

    command = [
        CLAMSCAN_PATH,
        "-r",
        str(target_dir),
        f"--move={QUARANTINE_DIR}",
        f"--log={log_file}"
    ]

    if MAX_SCAN_SIZE_MB:
        command.append(f"--max-scansize={MAX_SCAN_SIZE_MB}M")
    if MAX_FILE_SIZE_MB:
        command.append(f"--max-filesize={MAX_FILE_SIZE_MB}M")

    # command.append(str(folder))

    try:
        subprocess.run(command, check=True)
        log(f"Scan completed: {target_dir}", log_file)
    except subprocess.CalledProcessError:
        log(f"[!] Clamscan crashed on {target_dir}. Skipping.", crash_file)
    return log_file

    # Post-scan, log empty files
    with open(log_file, "r") as f:
        for line in f:
            if "Empty file" in line:
                log_to(EMPTY_LOG, line.strip())


def ensure_quarantine_writable(quarantine: Path):
    if quarantine.exists():
        for f in quarantine.iterdir():
            if f.is_file():
                f.unlink()
    quarantine.mkdir(parents=True, exist_ok=True)
    quarantine.chmod(0o755)


def finalize_quarantine(quarantine: Path):
    quarantine.chmod(0o700)

# ---------- MAIN SCRIPT ----------


def main():
    user_input = input("Enter the full path to the drive: ")
    drive_path = Path(sanitize_path(user_input))

    if not drive_path.exists():
        print("[!] Drive path does not exist.")
        sys.exit(1)

    drive_name = drive_path.name.replace(" ", "_")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    scan_log_dir = SCAN_LOG_BASE / f"{drive_name}_{timestamp}"
    scan_log_dir.mkdir(parents=True, exist_ok=True)

    ensure_quarantine_writable(QUARANTINE_DIR)

    top_dirs = [d for d in drive_path.iterdir() if d.is_dir()]
    if not top_dirs:
        top_dirs = [drive_path]  # If no subfolders, scan the root directly

    log_files = []
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_dir = {executor.submit(
            scan_directory, d, QUARANTINE_DIR, scan_log_dir): d for d in top_dirs}
        for future in as_completed(future_to_dir):
            log_file = future.result()
            log_files.append(log_file)

    finalize_quarantine(QUARANTINE_DIR)

    # Summary
    summary_file = scan_log_dir / "summary.txt"
    total_infected = 0
    for file in log_files:
        with open(file, 'r') as f:
            for line in f:
                if line.strip().endswith("FOUND"):
                    total_infected += 1

    log(f"Scan complete. Total infected files: {total_infected}", summary_file)
    print(f"\nAll logs saved in: {scan_log_dir.resolve()}")


if __name__ == "__main__":
    main()
