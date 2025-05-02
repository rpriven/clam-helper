# 🛡️ ClamScan Helper

**ClamScan Helper** is a Python-based utility designed to simplify and improve the process of scanning large or potentially infected external drives (e.g., portable USB drives, backups, client data) using ClamAV. It adds automation, error handling, logging, and quarantine management around `clamscan` for more robust and organized workflows.

---

## 🚀 Features

- 🔍 **Recursive Scanning per Folder**: Efficiently scans each top-level folder individually to avoid crashing on bad files.
- 📁 **Timestamped Log Directories**: Keeps scan logs grouped by scan session, avoiding overwrites and improving traceability.
- 🧼 **Drive Path Sanitization**: Accepts raw or escaped drive paths and formats them for consistent use.
- 📊 **Structured Logging**: Individual logs per folder, plus a summary and crash log to track scan health.
- 🧵 **Multithreaded Scanning**: Optional threading for faster processing on multi-core systems.
- 🔐 **Quarantine Management**:
    - Automatically sets quarantine permissions to writable during the scan and read-only after.
    - Moves infected files to a hidden `.quarantine` directory for safe isolation.

---

## 📦 Requirements

- Python 3.6+
- `clamav` and `clamscan` installed
- `clamscan` available in `$PATH`
- `clamonacc` (optional for real-time scanning)

---

## 🛠️ How to Use

1. **Connect External Drive**
2. **Run the Script**
    
    ```bash
    CopyEdit
    python3 scan-helper.py

3. **Follow Prompts**:
    - Enter the full path to the mounted drive (e.g., `/media/username/My Passport`).
    - The script will sanitize the name and begin scanning each folder one at a time.
4. **Review Logs**:
    - Logs are saved in `~/.clamscan_logs/<drive_name>_<timestamp>/`
    - Includes: per-folder logs, summary of infected files, and any crash-prone folders.

---

## 📁 Example Directory Structure

```
CopyEdit
~/.clamscan_logs/
  └── My_Passport_2025-05-01_1835/
      ├── 01_Users.log
      ├── 02_Backups.log
      ├── crash_summary.txt
      ├── infected_summary.txt
```

---

## 💡 Notes

- You can configure the number of threads and `clamscan` flags in the script settings.
- Folders that cause `clamscan` to crash will be listed in `crash_summary.txt` and skipped.
- A `.quarantine` directory is created in your home folder or specified location.

---

## 🧹 Future Improvements

- Regex-based folder/file exclusion
- Auto-delete empty files (optional)
- Real-time progress UI
- GUI wrapper (PyQt/Tkinter)
- Integration with `clamonacc` for live scanning

---

## ⚠️ Disclaimer

Use at your own risk. This tool is designed for tech-savvy users managing potentially compromised media. Be cautious with quarantined or moved files.
