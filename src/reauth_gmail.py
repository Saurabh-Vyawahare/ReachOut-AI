"""
Gmail Token Re-Authorization Helper
Run this to re-authorize each Gmail account one at a time.
It tells you EXACTLY which account to sign into before opening the browser.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from config import GMAIL_ACCOUNTS, GMAIL_CLIENT_SECRET

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def reauth_one(index: int):
    """Re-authorize a single Gmail account."""
    account = GMAIL_ACCOUNTS[index]
    email = account["email"]
    token_file = account["credentials_file"]

    # Delete old token if exists
    if Path(token_file).exists():
        os.remove(token_file)
        print(f"  Deleted old token: {token_file}")

    print(f"\n  ╔══════════════════════════════════════════════════╗")
    print(f"  ║  SIGN INTO: {email:<38}║")
    print(f"  ╚══════════════════════════════════════════════════╝")
    print(f"\n  A browser will open. Make sure you:")
    print(f"  1. Sign into EXACTLY this account: {email}")
    print(f"  2. If the wrong account is pre-selected, click 'Use another account'")
    print(f"  3. Click 'Allow' on the permissions screen")

    input(f"\n  Press ENTER when ready to open browser for {email}...")

    flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CLIENT_SECRET, SCOPES)
    creds = flow.run_local_server(port=0)

    Path(token_file).parent.mkdir(parents=True, exist_ok=True)
    with open(token_file, "w") as f:
        f.write(creds.to_json())

    print(f"\n  ✓ Token saved for {email}\n")


def main():
    print("\n  ═══ Gmail Re-Authorization ═══")
    print(f"  Found {len(GMAIL_ACCOUNTS)} accounts:\n")

    for i, acc in enumerate(GMAIL_ACCOUNTS):
        print(f"    {i + 1}. {acc['email']}")

    print(f"\n  We'll authorize them ONE AT A TIME.")
    print(f"  Pay attention to which account to sign into!\n")

    for i in range(len(GMAIL_ACCOUNTS)):
        email = GMAIL_ACCOUNTS[i]["email"]
        if not email:
            print(f"  Skipping account {i + 1} (not configured)")
            continue

        reauth_one(i)

        if i < len(GMAIL_ACCOUNTS) - 1:
            print(f"  ─── Next account coming up ───")

    print(f"\n  ═══ All accounts authorized! ═══")
    print(f"  Now run: python main.py\n")


if __name__ == "__main__":
    main()
