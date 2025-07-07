# KoboToolbox Batch Project Ownership Transfer

Easily transfer project ownership between two KoboToolbox users for many projects at once, with clear logs, error handling, and summary reporting.

## Features

- Transfer **many projects** from one user to another
- Supports all KoboToolbox servers via config (e.g. eu.kobotoolbox.org, kf.kobotoolbox.org, etc.)
- Handles already pending or completed transfers smartly
- Nice output with clear status icons (✅, 🔁, ❌, etc.)
- Generates a summary CSV report at the end

---

## Quick Start

### 1. Requirements

- Python 3.8+
- Install dependencies:

  ```sh
  pip install pandas requests
  ```

### 2. Prepare Your Files

#### `assets.xlsx`

A one-column Excel file listing all project (asset) UIDs to transfer:

| asset_uid               |
|-------------------------|
| aMwz6AwmxzQegdSaH9zMmU  |
| aS6vfgLPkmQYyRu7Pm8TJi  |

#### `credentials.json`

A JSON file with your Kobo server URL and both users' credentials (get API tokens from user profile settings):

```json
{
  "server": "https://eu.kobotoolbox.org",
  "sender_username": "your_sender_username",
  "sender_api_key": "SENDER_API_TOKEN",
  "receiver_username": "your_receiver_username",
  "receiver_api_key": "RECEIVER_API_TOKEN"
}
```

- The `server` can be any KoboToolbox instance (e.g. `https://eu.kobotoolbox.org`, `https://kf.kobotoolbox.org`, or your private Kobo server).

### 3. Run the Script

```sh
python batch_transfer.py
```

### 4. Review Results

- **Console output:** Icons show what happened for each project.
- **`transfer_summary.csv`:** Summary of all results.

---

## How It Works

For each asset/project UID:
1. **Checks if already transferred** (with correct direction: sender → receiver).
2. **If not transferred:**
    - Attempts to create a transfer invite
    - If already pending, skips to next step
    - Repeatedly checks for a pending invite (with retries)
    - Accepts the invite as the receiver
    - Waits between assets
3. Outputs a clear summary and CSV report.

---

## Output Example

```
🔄 Loading assets from 'assets.xlsx'...
🗂️  Assets to transfer: ['aMwz6AwmxzQegdSaH9zMmU', 'aS6vfgLPkmQYyRu7Pm8TJi']
🔄 Loading credentials from 'credentials.json'...
————————————————————————————————————————————————————
🔔 [1/2] aMwz6AwmxzQegdSaH9zMmU
  ✉️  Creating invite...
  ✅ Invite sent!
  🔍 Checking for pending invite... (1/8)
  🔗 Pending invite found.
  🤝 Accepting invite...
  ✅ Invite accepted!
  ⏳ Waiting 2 sec...
————————————————————————————————————————————————————
🔔 [2/2] aS6vfgLPkmQYyRu7Pm8TJi
  🔎 Already transferred: aS6vfgLPkmQYyRu7Pm8TJi
————————————————————————————————————————————————————

🎉 TRANSFER SUMMARY REPORT 🎉
  ✅ Success: 1
  🔁 Already transferred: 1
  ❌ Failed: 0

  ✅ aMwz6AwmxzQegdSaH9zMmU
  🔁 aS6vfgLPkmQYyRu7Pm8TJi

📄 Detailed summary saved as 'transfer_summary.csv'
————————————————————————————————————————————————————
```

---

## Troubleshooting

- **❌ Not the owner:** The sender must be the current owner of the project UID.
- **❌ Invite not found after retries:** Wait a bit longer or try again, especially for large accounts.
- **🔁 Already transferred:** The project was already transferred in the same direction (sender → receiver).
- **Credential errors:** Make sure both API tokens are correct and have the needed permissions.

---

## Advanced

- **Change wait/retry timing:** Edit `PAUSE_BETWEEN_ASSETS`, `INVITE_RETRY_COUNT`, and `INVITE_RETRY_DELAY` in the script.
- **Back-and-forth transfers:** The script tracks the most recent successful transfer. It will transfer again only if the last transfer was not in the current sender→receiver direction.
- **Works with any KoboToolbox instance:** Just update the `"server"` field in your config file.

---


**Made with ❤️ for KoboToolbox power users.**
