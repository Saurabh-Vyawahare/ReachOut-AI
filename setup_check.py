"""
ReachOut-AI v2.0 — Setup Checker
Run this first to verify all credentials and APIs are working.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

def check():
    from config import (
        XAI_API_KEY, ANTHROPIC_API_KEY, SERPAPI_KEY,
        SPREADSHEET_ID, GMAIL_ACCOUNTS, SHEETS_SERVICE_ACCOUNT
    )
    from pathlib import Path

    print("\n  ═══ ReachOut-AI v2.0 Setup Check ═══\n")
    ok = True

    # 1. API Keys
    checks = [
        ("XAI_API_KEY (Grok/Scout A)", bool(XAI_API_KEY), "Set XAI_API_KEY in .env"),
        ("ANTHROPIC_API_KEY (Haiku+Sonnet)", bool(ANTHROPIC_API_KEY), "Set ANTHROPIC_API_KEY in .env"),
        ("SERPAPI_KEY (Scout B)", bool(SERPAPI_KEY), "Set SERPAPI_KEY in .env (or skip Scout B)"),
        ("SPREADSHEET_ID", bool(SPREADSHEET_ID), "Set SPREADSHEET_ID in .env"),
    ]

    for label, passed, fix in checks:
        status = "✓" if passed else "✗"
        color = "" if passed else " ← FIX: " + fix
        print(f"  {status} {label}{color}")
        if not passed and "SERPAPI" not in label:
            ok = False

    # 2. Credential files
    print()
    cred_file = Path(SHEETS_SERVICE_ACCOUNT)
    if cred_file.exists():
        print(f"  ✓ Sheets service account: {cred_file}")
    else:
        print(f"  ✗ Missing: {cred_file}")
        ok = False

    # 3. Gmail accounts
    print()
    for i, acc in enumerate(GMAIL_ACCOUNTS):
        email = acc["email"]
        token = Path(acc["credentials_file"])
        if email:
            token_status = "token exists" if token.exists() else "needs auth"
            print(f"  {'✓' if token.exists() else '!'} Gmail {i+1}: {email} ({token_status})")
        else:
            print(f"  - Gmail {i+1}: not configured")

    # 4. Module imports
    print()
    modules = ["jd_analyzer", "scout_grok", "scout_serpapi", "validator",
               "email_generator", "quality_gate", "gmail_drafter", "reply_monitor"]
    for mod in modules:
        try:
            __import__(mod)
            print(f"  ✓ {mod}")
        except Exception as e:
            print(f"  ✗ {mod}: {e}")
            ok = False

    print()
    if ok:
        print("  All checks passed! Run: cd src && python main.py\n")
    else:
        print("  Some checks failed. Fix the issues above and re-run.\n")

if __name__ == "__main__":
    check()
