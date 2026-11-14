"""
Automated Cloud Publishing Dispatcher (Telegram Vault Edition)
Designed to run on GitHub Actions or a scheduled cloud worker.

Workflow:
1. Connects to Google Sheets via GOOGLE_SERVICE_ACCOUNT_JSON.
2. Reads the central workbook 'YouTube Content Pipeline & Dispatcher'.
3. Checks 'Task_Queue' for tasks matching the scheduled channel (ENGLISH at Midnight IST, HINDI at 4:30 PM IST).
4. Pulls video and metadata directly from the Telegram Cloud Vault (uncompressed doc file_id) via Telegram Bot API.
5. If NO fresh video is ready in Task_Queue:
   - Inspects the 'Backup_Pool' tab for the oldest available 'STANDBY' video.
   - Downloads the backup video and metadata from Telegram.
   - Uploads backup to YouTube.
   - Marks backup as 'USED' and pings Telegram:
     "⚠️ No fresh video today. Published backup: {title}. Remaining backups: {count}."
6. Uploads video to YouTube (Hindi or English channel).
7. Logs the video into the channel's archive tab.
8. Automatically updates live View, Like, and Comment counters across all channel tabs.
9. Cleans up temporary disk files (maintaining zero-bloat).
"""

import os
import sys
import json
import base64
import tempfile
import urllib.request
from datetime import datetime, timezone
import pytz

from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

MASTER_FOLDER_ID = "1b9MZR5idAK4EqLi2akxFX-FAMycA8rDe"
DEFAULT_SHEET_NAME = "YouTube Content Pipeline & Dispatcher"
SCOPES_YOUTUBE = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]


def get_google_clients():
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON secret.")

    if sa_json.strip().startswith("{"):
        creds_dict = json.loads(sa_json)
    else:
        creds_dict = json.loads(base64.b64decode(sa_json).decode("utf-8"))

    if "client_email" in creds_dict and creds_dict.get("type") == "service_account":
        scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scopes)
    elif "token" in creds_dict or "refresh_token" in creds_dict:
        token_scopes = creds_dict.get("scopes")
        creds = UserCredentials.from_authorized_user_info(creds_dict, scopes=token_scopes)
    else:
        raise ValueError("Unrecognized credentials format.")

    drive_service = build("drive", "v3", credentials=creds)
    sheets_service = build("sheets", "v4", credentials=creds)
    return drive_service, sheets_service


def get_youtube_client(channel_key):
    secret_key = "YOUTUBE_TOKEN_HINDI" if "HINDI" in channel_key.upper() else "YOUTUBE_TOKEN_ENGLISH"
    token_json = os.environ.get(secret_key)
    if not token_json:
        raise ValueError(f"Missing YouTube OAuth secret: {secret_key}")

    if token_json.strip().startswith("{"):
        token_data = json.loads(token_json)
    else:
        token_data = json.loads(base64.b64decode(token_json).decode("utf-8"))

    token_scopes = token_data.get("scopes") or SCOPES_YOUTUBE
    creds = UserCredentials.from_authorized_user_info(token_data, scopes=token_scopes)
    return build("youtube", "v3", credentials=creds)


def find_spreadsheet_id(drive_service, sheet_name):
    q = f"'{MASTER_FOLDER_ID}' in parents and name = '{sheet_name}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    res = drive_service.files().list(q=q, fields="files(id, name)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    q2 = f"name = '{sheet_name}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    res2 = drive_service.files().list(q=q2, fields="files(id, name)").execute()
    files2 = res2.get("files", [])
    if files2:
        return files2[0]["id"]
    raise FileNotFoundError(f"Spreadsheet '{sheet_name}' not found.")


def send_telegram_alert(text: str):
    bot_token = (os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").split("#")[0].strip()
    chat_id = (os.environ.get("CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("MY_TELEGRAM_CHAT_ID") or "5267470220").split("#")[0].strip()
    if not bot_token or not chat_id:
        print("[-] Skipping Telegram alert: BOT_TOKEN or CHAT_ID not set.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print("[+] Telegram alert sent successfully.")
    except Exception as e:
        print(f"[!] Warning: Failed to send Telegram alert: {e}")


def download_telegram_file(file_id: str, dest_path: str):
    bot_token = (os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").split("#")[0].strip()
    if not bot_token:
        raise ValueError("Missing BOT_TOKEN or TELEGRAM_BOT_TOKEN.")

    api_id_raw = (os.environ.get("TELEGRAM_API_ID") or "30360141").split("#")[0].strip()
    api_id = int(api_id_raw)
    api_hash = (os.environ.get("TELEGRAM_API_HASH") or "ecb0dc6dbe73524409a14f7dfff7b6e2").split("#")[0].strip()

    # 1. Try standard getFile first (instant for metadata and files <= 20MB)
    try:
        print(f"[*] Resolving Telegram file_id: {file_id}")
        url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("ok"):
            file_path = data["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            print(f"[*] Downloading file via Telegram Bot API...")
            urllib.request.urlretrieve(download_url, dest_path)
            sz_mb = os.path.getsize(dest_path) / (1024 * 1024)
            print(f"[+] Download complete: {dest_path} ({sz_mb:.2f} MB)")
            return
    except urllib.error.HTTPError as e:
        print(f"[*] Standard Bot API download returned {e.code} (File > 20MB). Switching to MTProto client...")
    except Exception as e:
        print(f"[*] Bot API download error: {e}. Switching to MTProto client...")

    # 2. MTProto download via Pyrogram for video files > 20MB
    print(f"[*] Downloading large media file via Telegram MTProto client...")
    import asyncio
    from pyrogram import Client

    async def _mtproto_download():
        async with Client("gh_bot_session", api_id=api_id, api_hash=api_hash, bot_token=bot_token, in_memory=True) as app:
            dl_path = await app.download_media(file_id, file_name=dest_path)
            if dl_path != dest_path and os.path.exists(dl_path):
                import shutil
                shutil.move(dl_path, dest_path)

    asyncio.run(_mtproto_download())
    if not os.path.exists(dest_path):
        raise FileNotFoundError(f"Failed to download Telegram file to {dest_path}")
    sz_mb = os.path.getsize(dest_path) / (1024 * 1024)
    print(f"[+] MTProto Download complete: {dest_path} ({sz_mb:.2f} MB)")


def parse_metadata_file(content_text):
    data = {
        "topic": "General Curiosity",
        "title": "Daily Explainer Video",
        "description": "",
        "tags": ["facts", "shorts", "stickman", "animation"],
        "category_id": "27",
        "privacy": "public"
    }
    lines = content_text.splitlines()
    current_section = None
    desc_lines = []

    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()
        if upper in ["TITLE:", "TITLE"]:
            current_section = "title"
            continue
        elif upper in ["DESCRIPTION:", "DESCRIPTION"]:
            current_section = "description"
            continue
        elif upper in ["HASHTAGS:", "TAGS:", "HASHTAGS", "TAGS"]:
            current_section = "tags"
            continue
        elif upper in ["TOPIC:", "TOPIC"]:
            current_section = "topic"
            continue

        if ":" in line and current_section is None:
            k, v = line.split(":", 1)
            kl = k.strip().lower()
            vl = v.strip()
            if kl == "title":
                data["title"] = vl
            elif kl == "topic":
                data["topic"] = vl
            elif kl in ["tags", "hashtags"]:
                data["tags"] = [t.strip().replace("#", "") for t in vl.split(",") if t.strip()]
            elif kl == "description":
                data["description"] = vl
            elif kl == "privacy":
                data["privacy"] = vl
            continue

        if current_section == "title" and stripped:
            data["title"] = stripped
            data["topic"] = stripped.split("(")[0].replace("?", "").strip()
            current_section = None
        elif current_section == "topic" and stripped:
            data["topic"] = stripped
            current_section = None
        elif current_section == "description":
            desc_lines.append(line)
        elif current_section == "tags" and stripped:
            if "#" in stripped:
                raw_tags = [t.strip("#").strip() for t in stripped.split() if t.strip()]
                data["tags"].extend(raw_tags)
            else:
                raw_tags = [t.strip() for t in stripped.split(",") if t.strip()]
                data["tags"].extend(raw_tags)

    if desc_lines:
        data["description"] = "\n".join(desc_lines).strip()

    return data


def upload_video_to_youtube(youtube_service, file_path, meta):
    print(f"[*] Uploading to YouTube: '{meta['title']}' [{meta['privacy']}]")
    body = {
        "snippet": {
            "title": meta["title"][:100],
            "description": meta["description"],
            "tags": meta["tags"],
            "categoryId": meta.get("category_id", "27")
        },
        "status": {
            "privacyStatus": meta.get("privacy", "public"),
            "selfDeclaredMadeForKids": False
        }
    }
    media = MediaFileUpload(file_path, chunksize=1024*1024*5, resumable=True, mimetype="video/mp4")
    request = youtube_service.videos().insert(part=",".join(body.keys()), body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"    YouTube Upload: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    watch_url = f"https://youtu.be/{video_id}"
    print(f"[+] Upload successful! Video URL: {watch_url}")
    return video_id, watch_url


def update_view_counters(youtube_services, sheets_service, spreadsheet_id, channel_tabs):
    print("\n[*] Updating view counters & statistics for published videos...")
    for tab_name, channel_key in channel_tabs.items():
        yt = youtube_services.get(channel_key)
        if not yt:
            continue
        # Skip statistics update if channel token only has upload scope (requires readonly scope)
        token_json = os.environ.get(f"YOUTUBE_TOKEN_{channel_key}", "")
        if token_json and '"youtube.upload"' in token_json and '"youtube.readonly"' not in token_json:
            print(f"[*] Skipping stats update for {tab_name} (token is upload-only).")
            continue
        try:
            res = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{tab_name}'!A1:G100"
            ).execute()
            rows = res.get("values", [])
            if len(rows) <= 1:
                continue

            for row_idx, r in enumerate(rows[1:], start=2):
                if len(r) >= 7 and r[6]:
                    vid = r[6].strip()
                    if vid and len(vid) >= 10:
                        try:
                            stat_res = yt.videos().list(part="statistics", id=vid).execute()
                            items = stat_res.get("items", [])
                            if items:
                                stats = items[0]["statistics"]
                                views = stats.get("viewCount", "0")
                                likes = stats.get("likeCount", "0")
                                comments = stats.get("commentCount", "0")
                                sheets_service.spreadsheets().values().update(
                                    spreadsheetId=spreadsheet_id,
                                    range=f"'{tab_name}'!C{row_idx}:E{row_idx}",
                                    valueInputOption="USER_ENTERED",
                                    body={"values": [[views, likes, comments]]}
                                ).execute()
                        except Exception as e:
                            print(f"    [!] Failed to update stats for {vid}: {e}")
        except Exception as e:
            print(f"[!] Warning reading tab '{tab_name}': {e}")


def process_queue():
    sheet_name = os.environ.get("TRACKING_SHEET_NAME", DEFAULT_SHEET_NAME)
    drive_service, sheets_service = get_google_clients()
    spreadsheet_id = find_spreadsheet_id(drive_service, sheet_name)
    print(f"[*] Connected to Spreadsheet: '{sheet_name}' (ID: {spreadsheet_id})")

    now_utc = datetime.now(timezone.utc)
    ist_tz = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist_tz)
    print(f"[*] Current IST Time: {now_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    channel_tabs = {
        "Daily Fun Facts (Hindi)": "HINDI",
        "How Did That Happen (English)": "ENGLISH"
    }
    youtube_services = {
        "HINDI": get_youtube_client("HINDI"),
        "ENGLISH": get_youtube_client("ENGLISH")
    }

    dispatch_channel = os.environ.get("DISPATCH_CHANNEL", "ALL").strip().upper()
    allowed_channel = None
    if dispatch_channel in ["ENGLISH", "HINDI"]:
        allowed_channel = dispatch_channel
        print(f"[*] Manual dispatch override: processing strictly {allowed_channel} videos.")
    else:
        if 22 <= now_ist.hour or now_ist.hour < 3:
            allowed_channel = "ENGLISH"
            print(f"[*] Time slot detected: Midnight window -> processing strictly ENGLISH videos.")
        elif 15 <= now_ist.hour < 19:
            allowed_channel = "HINDI"
            print(f"[*] Time slot detected: Evening rush window (4:30 PM) -> processing strictly HINDI videos.")
        else:
            print(f"[*] Outside designated upload windows ({now_ist.strftime('%H:%M')} IST). Updating counters only.")
            update_view_counters(youtube_services, sheets_service, spreadsheet_id, channel_tabs)
            return

    # 1. READ TASK QUEUE
    queue_res = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Task_Queue!A1:J100"
    ).execute()
    queue_rows = queue_res.get("values", [])

    task_found = False

    if queue_rows and len(queue_rows) > 1:
        headers = [h.strip() for h in queue_rows[0]]
        for row_idx, row in enumerate(queue_rows[1:], start=2):
            row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            status = row_dict.get("Status", "").strip().upper()
            target_channel = row_dict.get("Target_Channel", "HINDI").strip().upper()
            channel_key = "HINDI" if "HINDI" in target_channel else "ENGLISH"

            if channel_key != allowed_channel:
                continue

            if status in ["READY_FOR_UPLOAD", "PENDING", "APPROVED"]:
                sched_time_str = row_dict.get("Scheduled_Time_UTC", "").strip()
                if sched_time_str:
                    try:
                        sched_dt = datetime.fromisoformat(sched_time_str.replace("Z", "+00:00"))
                        if sched_dt > now_utc:
                            print(f"[-] Task at row {row_idx} scheduled for {sched_time_str} is in the future. Skipping.")
                            continue
                    except Exception as e:
                        print(f"[!] Warning parsing time '{sched_time_str}': {e}")

                tg_file_id = row_dict.get("Telegram_File_ID", "").strip()
                tg_meta_id = row_dict.get("Telegram_Meta_ID", "").strip()

                if not tg_file_id:
                    print(f"[-] Task at row {row_idx} missing Telegram_File_ID. Checking Drive fallback...")
                    continue

                print(f"\n[>>>] Processing Fresh Task at row {row_idx} for channel '{channel_key}'")
                task_found = True

                with tempfile.TemporaryDirectory() as tmp_dir:
                    video_path = os.path.join(tmp_dir, "upload_video.mp4")
                    download_telegram_file(tg_file_id, video_path)

                    meta = {
                        "topic": row_dict.get("Topic") or "Daily Explainer",
                        "title": row_dict.get("Video_Title") or "Daily Short",
                        "description": "#Shorts #Facts #Curiosity",
                        "tags": ["facts", "stickman", "shorts", "animation"],
                        "category_id": "27",
                        "privacy": "public"
                    }

                    if tg_meta_id:
                        meta_path = os.path.join(tmp_dir, "metadata.txt")
                        try:
                            download_telegram_file(tg_meta_id, meta_path)
                            with open(meta_path, "r", encoding="utf-8") as mf:
                                parsed = parse_metadata_file(mf.read())
                                meta.update(parsed)
                        except Exception as e:
                            print(f"[!] Warning reading metadata doc: {e}")

                    if row_dict.get("Video_Title"):
                        meta["title"] = row_dict["Video_Title"]

                    yt_service = youtube_services[channel_key]
                    vid_id, watch_url = upload_video_to_youtube(yt_service, video_path, meta)

                    # Mark Task_Queue as PUBLISHED
                    status_col_idx = headers.index("Status") if "Status" in headers else 5
                    col_letter = chr(ord('A') + status_col_idx)
                    sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f"Task_Queue!{col_letter}{row_idx}",
                        valueInputOption="USER_ENTERED",
                        body={"values": [["PUBLISHED"]]}
                    ).execute()

                    # Archive into the Channel Tab: ['Video_Title', 'Video_URL', 'Views', 'Likes', 'Comments', 'Uploaded_Time', 'Video_ID']
                    dest_tab = "Daily Fun Facts (Hindi)" if channel_key == "HINDI" else "How Did That Happen (English)"
                    archive_row = [
                        meta["title"],
                        watch_url,
                        "0", "0", "0",
                        now_ist.strftime("%Y-%m-%d %H:%M IST"),
                        vid_id
                    ]
                    sheets_service.spreadsheets().values().append(
                        spreadsheetId=spreadsheet_id,
                        range=f"'{dest_tab}'!A1",
                        valueInputOption="USER_ENTERED",
                        body={"values": [archive_row]}
                    ).execute()

                    send_telegram_alert(
                        f"🎉 YouTube Upload Complete!\n\n"
                        f"📌 Channel: {dest_tab}\n"
                        f"🎬 Title: {meta['title']}\n"
                        f"🔗 Link: {watch_url}\n"
                        f"🕒 Uploaded: {now_ist.strftime('%Y-%m-%d %H:%M IST')}"
                    )
                break

    # 2. FAILOVER TO BACKUP_POOL IF NO FRESH TASK WAS PROCESSED
    if not task_found:
        print(f"\n[!] No ready task found in Task_Queue for {allowed_channel}. Checking Backup_Pool...")
        try:
            pool_res = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range="Backup_Pool!A1:H50"
            ).execute()
            pool_rows = pool_res.get("values", [])

            if pool_rows and len(pool_rows) > 1:
                p_headers = [h.strip() for h in pool_rows[0]]
                backup_row_to_use = None
                backup_row_idx = None
                remaining_backups = 0

                for p_idx, p_row in enumerate(pool_rows[1:], start=2):
                    p_dict = {p_headers[i]: p_row[i] if i < len(p_row) else "" for i in range(len(p_headers))}
                    p_status = p_dict.get("Status", "").strip().upper()
                    p_channel = p_dict.get("Channel", "").strip().upper()

                    if p_status == "STANDBY" and (allowed_channel in p_channel or p_channel in allowed_channel):
                        if backup_row_to_use is None:
                            backup_row_to_use = p_dict
                            backup_row_idx = p_idx
                        else:
                            remaining_backups += 1

                if backup_row_to_use:
                    print(f"[+] Deploying backup video: '{backup_row_to_use.get('Title')}' (Remaining: {remaining_backups})")
                    tg_file_id = backup_row_to_use.get("Telegram_File_ID", "").strip()
                    tg_meta_id = backup_row_to_use.get("Telegram_Meta_ID", "").strip()

                    with tempfile.TemporaryDirectory() as tmp_dir:
                        video_path = os.path.join(tmp_dir, "backup_video.mp4")
                        download_telegram_file(tg_file_id, video_path)

                        meta = {
                            "topic": backup_row_to_use.get("Topic") or "Evergreen Explainer",
                            "title": backup_row_to_use.get("Title") or "Evergreen Short",
                            "description": "#Shorts #Facts #Curiosity",
                            "tags": ["facts", "stickman", "shorts", "animation"],
                            "category_id": "27",
                            "privacy": "public"
                        }
                        if tg_meta_id:
                            meta_path = os.path.join(tmp_dir, "metadata.txt")
                            try:
                                download_telegram_file(tg_meta_id, meta_path)
                                with open(meta_path, "r", encoding="utf-8") as mf:
                                    parsed = parse_metadata_file(mf.read())
                                    meta.update(parsed)
                            except Exception as e:
                                print(f"[!] Warning reading backup metadata: {e}")

                        yt_service = youtube_services[allowed_channel]
                        vid_id, watch_url = upload_video_to_youtube(yt_service, video_path, meta)

                        # Mark as USED in Backup_Pool
                        p_status_idx = p_headers.index("Status") if "Status" in p_headers else 5
                        p_col_letter = chr(ord('A') + p_status_idx)
                        sheets_service.spreadsheets().values().update(
                            spreadsheetId=spreadsheet_id,
                            range=f"Backup_Pool!{p_col_letter}{backup_row_idx}",
                            valueInputOption="USER_ENTERED",
                            body={"values": [["USED"]]}
                        ).execute()

                        dest_tab = "Daily Fun Facts (Hindi)" if allowed_channel == "HINDI" else "How Did That Happen (English)"
                        archive_row = [
                            meta["title"],
                            watch_url,
                            "0", "0", "0",
                            now_ist.strftime("%Y-%m-%d %H:%M IST"),
                            vid_id
                        ]
                        sheets_service.spreadsheets().values().append(
                            spreadsheetId=spreadsheet_id,
                            range=f"'{dest_tab}'!A1",
                            valueInputOption="USER_ENTERED",
                            body={"values": [archive_row]}
                        ).execute()

                        # Send Telegram Emergency Notification
                        alert_msg = (
                            f"⚠️ AUTOMATION NOTICE: NO NEW VIDEO FOUND TODAY\n"
                            f"-----------------------------------------------\n"
                            f"📌 Channel: {dest_tab}\n"
                            f"🎬 Title: {meta['title']}\n"
                            f"🔗 Link: {watch_url}\n"
                            f"🕒 Uploaded: {now_ist.strftime('%Y-%m-%d %H:%M IST')}\n\n"
                            f"🚨 Backlog Status: Only {remaining_backups} standby backup(s) remaining in pool!\n"
                            f"Please render new videos to refill the safety buffer."
                        )
                        send_telegram_alert(alert_msg)
                else:
                    print(f"[-] No STANDBY videos found in Backup_Pool for channel {allowed_channel}.")
                    send_telegram_alert(
                        f"🚨 CRITICAL WARNING: No fresh video scheduled AND Backup_Pool is EMPTY for {allowed_channel}!\n"
                        f"No video could be published today. Please generate new content immediately."
                    )
        except Exception as e:
            print(f"[!] Warning querying Backup_Pool: {e}")

    # 3. Live update statistics for all channel videos
    update_view_counters(youtube_services, sheets_service, spreadsheet_id, channel_tabs)


if __name__ == "__main__":
    process_queue()
