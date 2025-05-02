# clam-helper.py

import os
import sys
import shutil
import datetime
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, *args, **kwargs): return x  # dummy passthrough
try:
    from termcolor import colored
except ImportError:
    def colored(text, *args, **kwargs): return text


# === CONFIGURABLE ===
MAX_THREADS = 4
QUARANTINE_DIR = Path.home() / ".quarantine"
SCAN_LOG_BASE = Path.home() / ".clamscan_logs"
CRASH_LOG = SCAN_LOG_BASE / "crash_summary.txt"
EMPTY_LOG = SCAN_LOG_BASE / "empty_files.txt"
INFECTED_LOG = SCAN_LOG_BASE / "infected_files.txt"
SUMMARY_LOG = SCAN_LOG_BASE / "summary.txt"
MAX_SCAN_SIZE_MB = 200  # Optional: set to None to omit
MAX_FILE_SIZE_MB = 100  # Optional: set to None to omit
CLAMSCAN_PATH = shutil.which("clamscan") or "/usr/bin/clamscan"

# === HELPERS ===

parser = argparse.ArgumentParser()
parser.add_argument("-ql", "--quarantine-location", type=str, default=QUARANTINE_DIR,
                    help="Alternate path for quarantine storage.")
parser.add_argument("--purge", action="store_true",
                    help="Delete all files in quarantine after scanning.")
args = parser.parse_args()

quarantine_path = Path(
    args.quarantine_location) if args.quarantine_location else QUARANTINE_DIR / ".quarantine"


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


def fast_folder_list(root: Path, max_depth=5):
    try:
        # Use 'fd' if available
        out = subprocess.check_output(
            ["fd", "--type", "d", f"--max-depth={max_depth}", ".", str(root)], text=True)
        return [Path(p) for p in out.strip().splitlines()]
    except Exception:
        try:
            # Use 'find' fallback
            out = subprocess.check_output(
                ["find", str(root), "-type", "d", "--maxdepth", str(max_depth)], text=True)
            return [Path(p) for p in out.strip().splitlines()]
        except Exception:
            # Fallback to Python
            folders = []
            for dirpath, dirnames, _ in os.walk(root):
                depth = len(Path(dirpath).relative_to(root).parts)
                if depth <= max_depth:
                    folders.append(Path(dirpath))
            return folders


def scan_directory(target_dir: Path, quarantine: Path, log_dir: Path, drive_path: Path) -> Path:
    print("Launching scan on {target_dir}...")
    log_file = log_dir / f"scan_{target_dir.name}.log"
    crash_file = log_dir / "crash_summary.txt"

    command = [
        CLAMSCAN_PATH,
        "--bell",
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
        for sub in target_dir.iterdir():
            if sub.is_dir():
                try:
                    scan_directory(..., quarantine_path, ...)
                except Exception as e:
                    log(f"Subfolder scan also failed: {sub} | Reason: {e}", crash_file)
    else:
        log(f"Max recursion depth {len(Path(target_dir).is_relative_to(drive_path).parts)} hit. Skipping deeper folders in {target_dir}.", crash_file)

    return log_file

    # Post-scan, log empty files
    with open(log_file, "r") as f:
        for line in f:
            if "Empty file" in line:
                log_to(EMPTY_LOG, line.strip())
            elif "FOUND" in line:
                with open(INFECTED_LOG, "a") as infected_log:
                    infected_log.write(f"{datetime.now().isoformat()} | {line.strip()}\n")


def ensure_quarantine_writable(quarantine_path):
    if quarantine_path.exists():
        for f in quarantine_path.iterdir():
            if f.is_file():
                print(f"Removing stale file: {f}", "yellow")
                f.unlink()
    quarantine_path.mkdir(parents=True, exist_ok=True)
    quarantine_path.chmod(0o755)
    print(f"Quarantine ready and writable: {quarantine_path}", "green")


def finalize_quarantine(quarantine_path):
    quarantine_path.chmod(0o700)
    print(f"Quarantine permissions secured: {quarantine_path}", "cyan")

    # Make files immutable
    for f in quarantine_path.iterdir():
        if f.is_file():
            subprocess.run(["chattr", "+i", str(f)], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            print(f"Locked file with chattr +i: {f}", "magenta")

    # print contents of quarantine_path
    print("Quarantine contents:")
    for f in quarantine_path.iterdir():
        print(f" - {f.name}")

    print(f"[!] Quarantine still contains {len(list(quarantine_path.iterdir()))} files after scan.")

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

    # top_dirs = [d for d in drive_path.iterdir() if d.is_dir()]
    # top_dirs = [d for d in drive_path.rglob("*") if d.is_dir()]
    # if not top_dirs:
    # top_dirs = [drive_path]  # If no subfolders, scan the root directly
    top_dirs = fast_folder_list(drive_path, max_depth=5)

    pbar = tqdm(total=len(top_dirs), desc="Scanning folders", unit="dir")

    log_files = []
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_dir = {executor.submit(
            scan_directory, d, QUARANTINE_DIR, scan_log_dir): d for d in top_dirs}
        for future in as_completed(future_to_dir):
            log_file = future.result()
            log_files.append(log_file)
            pbar.update(1)

        pbar.close()

    finalize_quarantine(QUARANTINE_DIR)

    # Summary
    summary_file = scan_log_dir / "summary.txt"
    total_infected = 0
    for file in log_files:
        with open(file, 'r') as f:
            for line in f:
                if line.strip().endswith("FOUND"):
                    total_infected += 1

    if args.purge:
        for file in QUARANTINE_DIR.glob("*"):
            file.unlink()
        print("[✓] Quarantine purged.")
    else:
        choice = input("Do you want to purge quarantine? [y/N]: ").lower().strip()
        if choice == 'y':
            for file in QUARANTINE_DIR.glob("*"):
                file.unlink()
            print("[✓] Quarantine purged.")
        else:
            print(f"[!] Quarantine left intact with {len(list(QUARANTINE_DIR.iterdir()))} file(s).")

    log(f"Scan complete. Total infected files: {total_infected}", summary_file)
    print(f"\nAll logs saved in: {scan_log_dir.resolve()}")


if __name__ == "__main__":
    main()
