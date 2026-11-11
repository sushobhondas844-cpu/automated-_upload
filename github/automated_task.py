"""
Automated Task: Local Output -> Telegram Media Vault Sync & Cleanup
Monitors 'output/English' and 'output/Hindi' for rendered videos and metadata.
Vaults them to Telegram as uncompressed documents, logs File IDs into Task_Queue,
and deletes the local video and metadata files upon confirmed upload.
"""

import os
import sys
import time
from github.auto_sync_watcher import scan_once

if __name__ == "__main__":
    count = scan_once()
    if count == 0:
        print("[*] Automated Task: No new pending videos found in output/English or output/Hindi.")
    else:
        print(f"[+] Automated Task: Successfully vaulted {count} video package(s) to Telegram and Task_Queue.")
