import pandas as pd
import requests
import time
import json

ASSET_FILE = "assets.xlsx"
CREDENTIALS_FILE = "credentials.json"

PAUSE_BETWEEN_ASSETS = 2
INVITE_RETRY_COUNT = 8
INVITE_RETRY_DELAY = 2

def print_separator():
    print("—" * 52)

def asset_already_transferred(asset_uid, sender_username, receiver_username, sender_api_key, KOBO_BASE_URL):
    url = f"{KOBO_BASE_URL}/api/v2/project-ownership/invites/"
    headers = {"Authorization": f"Token {sender_api_key}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"⚠️ Could not check transfer history for {asset_uid}")
        return False
    invites = response.json().get('results', [])
    sender_url = f"{KOBO_BASE_URL}/api/v2/users/{sender_username}/"
    recipient_url = f"{KOBO_BASE_URL}/api/v2/users/{receiver_username}/"
    transfer_history = []
    for invite in invites:
        if invite.get('status') == "complete":
            for transfer in invite.get('transfers', []):
                asset_url = transfer.get('asset', '')
                if asset_url.endswith(f"/{asset_uid}/") and transfer.get('status') == "success":
                    transfer_history.append({
                        "date_modified": invite.get("date_modified"),
                        "sender": invite.get("sender"),
                        "recipient": invite.get("recipient"),
                        "invite_url": invite.get("url")
                    })
    if transfer_history:
        transfer_history.sort(key=lambda x: x['date_modified'], reverse=True)
        last_transfer = transfer_history[0]
        if (last_transfer['sender'] == sender_url and last_transfer['recipient'] == recipient_url):
            print(f"🔎 Already transferred: {asset_uid}")
            return True
    return False

def create_invite(asset_uid, recipient_username, sender_api_key, KOBO_BASE_URL):
    recipient_url = f"{KOBO_BASE_URL}/api/v2/users/{recipient_username}/"
    url = f"{KOBO_BASE_URL}/api/v2/project-ownership/invites/"
    headers = {
        "Authorization": f"Token {sender_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "recipient": recipient_url,
        "assets": [asset_uid],
    }
    print(f"  ✉️  Creating invite...")
    r = requests.post(url, headers=headers, json=data)
    if r.status_code == 201:
        print(f"  ✅ Invite sent!")
        return True, None
    elif r.status_code == 400:
        error_text = r.text
        if ("already has a pending invite" in error_text or 
            "cannot be transferred. Current status: pending" in error_text):
            print(f"  ⏳ Invite already pending, will try to accept.")
            return True, "pending_exists"
        elif "must be the owner" in error_text:
            print(f"  ❌ Not the owner.")
            return False, "not_owner"
    print(f"  ❌ Invite creation failed! ({r.status_code})")
    return False, r.text

def get_pending_invite_id(asset_uid, sender_username, receiver_api_key, KOBO_BASE_URL):
    url = f"{KOBO_BASE_URL}/api/v2/project-ownership/invites/"
    headers = {"Authorization": f"Token {receiver_api_key}"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"  ❌ Cannot check for pending invites!")
        return None
    invites = r.json().get('results', [])
    sender_url = f"{KOBO_BASE_URL}/api/v2/users/{sender_username}/"
    for invite in invites:
        if invite.get('sender') == sender_url and invite.get('status') == "pending":
            for transfer in invite.get('transfers', []):
                asset_url = transfer.get('asset', '')
                if asset_url.endswith(f"/{asset_uid}/") and transfer.get('status') == "pending":
                    print(f"  🔗 Pending invite found.")
                    return invite['url'].rstrip('/').split('/')[-1]
    print(f"  ❌ Pending invite not found.")
    return None

def accept_invite(invite_id, receiver_api_key, KOBO_BASE_URL):
    url = f"{KOBO_BASE_URL}/api/v2/project-ownership/invites/{invite_id}/"
    headers = {
        "Authorization": f"Token {receiver_api_key}",
        "Content-Type": "application/json"
    }
    data = {"status": "accepted"}
    print(f"  🤝 Accepting invite...")
    r = requests.patch(url, headers=headers, json=data)
    if r.status_code == 200:
        print(f"  ✅ Invite accepted!")
        return True, None
    else:
        print(f"  ❌ Accept failed! ({r.status_code})")
        return False, r.text

if __name__ == "__main__":
    print("🔄 Loading assets from 'assets.xlsx'...")
    df = pd.read_excel(ASSET_FILE)
    asset_uids = df['asset_uid'].dropna().astype(str).tolist()
    print(f"🗂️  Assets to transfer: {asset_uids}")
    print("🔄 Loading credentials from 'credentials.json'...")

    with open(CREDENTIALS_FILE, "r") as f:
        creds = json.load(f)

    KOBO_BASE_URL = creds['server'].rstrip("/")
    sender_username = creds['sender_username']
    sender_api_key = creds['sender_api_key']
    receiver_username = creds['receiver_username']
    receiver_api_key = creds['receiver_api_key']

    summary = []

    for i, asset_uid in enumerate(asset_uids, 1):
        print_separator()
        print(f"🔔 [{i}/{len(asset_uids)}] {asset_uid}")

        if asset_already_transferred(asset_uid, sender_username, receiver_username, sender_api_key, KOBO_BASE_URL):
            summary.append({
                "asset_uid": asset_uid,
                "status": "ALREADY TRANSFERRED",
                "error": None
            })
            continue

        ok, invite_error = create_invite(asset_uid, receiver_username, sender_api_key, KOBO_BASE_URL)
        if not ok and invite_error != "pending_exists":
            summary.append({
                "asset_uid": asset_uid,
                "status": "FAILED - Invite not created",
                "error": invite_error
            })
            continue

        invite_id = None
        for attempt in range(1, INVITE_RETRY_COUNT+1):
            print(f"  🔍 Checking for pending invite... ({attempt}/{INVITE_RETRY_COUNT})")
            invite_id = get_pending_invite_id(asset_uid, sender_username, receiver_api_key, KOBO_BASE_URL)
            if invite_id:
                break
            if attempt < INVITE_RETRY_COUNT:
                time.sleep(INVITE_RETRY_DELAY)
        if not invite_id:
            summary.append({
                "asset_uid": asset_uid,
                "status": "FAILED - Pending invite not found",
                "error": "Invite not found after retries"
            })
            continue

        accepted, accept_error = accept_invite(invite_id, receiver_api_key, KOBO_BASE_URL)
        if accepted:
            summary.append({
                "asset_uid": asset_uid,
                "status": "SUCCESS",
                "error": None
            })
        else:
            summary.append({
                "asset_uid": asset_uid,
                "status": "FAILED - Could not accept",
                "error": accept_error
            })

        print(f"  ⏳ Waiting {PAUSE_BETWEEN_ASSETS} sec...")
        time.sleep(PAUSE_BETWEEN_ASSETS)

    print_separator()
    print("\n🎉 TRANSFER SUMMARY REPORT 🎉")
    success_count = sum(1 for s in summary if s['status'] == "SUCCESS")
    already_transferred_count = sum(1 for s in summary if s['status'] == "ALREADY TRANSFERRED")
    fail_count = len(summary) - success_count - already_transferred_count
    print(f"  ✅ Success: {success_count}")
    print(f"  🔁 Already transferred: {already_transferred_count}")
    print(f"  ❌ Failed: {fail_count}\n")

    for item in summary:
        if item['status'] == "SUCCESS":
            print(f"  ✅ {item['asset_uid']}")
        elif item['status'] == "ALREADY TRANSFERRED":
            print(f"  🔁 {item['asset_uid']}")
        else:
            print(f"  ❌ {item['asset_uid']} — {item['status']}")
            if item['error']:
                print(f"      Error: {item['error']}\n")

    pd.DataFrame(summary).to_csv("transfer_summary.csv", index=False)
    print("\n📄 Detailed summary saved as 'transfer_summary.csv'")
    print_separator()
