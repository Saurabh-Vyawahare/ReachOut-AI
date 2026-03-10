"""
Setup Checker
Run this first to verify all credentials and connections are working.
Usage: python setup_check.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CHECKS = []


def check(name, condition, fix):
    status = "PASS" if condition else "FAIL"
    CHECKS.append((name, status, fix))


def main():
    print("\n" + "="*60)
    print("  COLD EMAIL AUTOMATION - SETUP CHECKER")
    print("="*60 + "\n")

    # 1. .env file
    check(
        ".env file exists",
        Path(".env").exists(),
        "Copy .env.example to .env and fill in your API keys"
    )

    # 2. Apollo API Key
    check(
        "Apollo API key set",
        bool(os.getenv("APOLLO_API_KEY")),
        "Add APOLLO_API_KEY to .env (get from Apollo Settings > API)"
    )

    # 3. Google CSE API Key
    check(
        "Google Custom Search API key set",
        bool(os.getenv("GOOGLE_CSE_API_KEY")),
        "Add GOOGLE_CSE_API_KEY to .env (Google Cloud Console > APIs)"
    )

    # 4. Google CSE ID
    check(
        "Google Custom Search Engine ID set",
        bool(os.getenv("GOOGLE_CSE_ID")),
        "Add GOOGLE_CSE_ID to .env (programmablesearchengine.google.com)"
    )

    # 5. OpenAI API Key
    check(
        "OpenAI API key set",
        bool(os.getenv("OPENAI_API_KEY")),
        "Add OPENAI_API_KEY to .env"
    )

    # 6. Spreadsheet ID
    check(
        "Google Sheet ID set",
        bool(os.getenv("SPREADSHEET_ID")),
        "Add SPREADSHEET_ID to .env (from your Google Sheet URL)"
    )

    # 7. Gmail accounts
    gmail_count = sum(1 for i in range(1, 5) if os.getenv(f"GMAIL_{i}"))
    check(
        f"Gmail accounts configured ({gmail_count}/4)",
        gmail_count >= 1,
        "Add GMAIL_1 through GMAIL_4 to .env"
    )

    # 8. Service account credentials
    check(
        "Sheets service account JSON exists",
        Path("credentials/sheets_service_account.json").exists(),
        "Download service account JSON from Google Cloud Console"
    )

    # 9. Gmail OAuth client secret
    check(
        "Gmail OAuth client secret exists",
        Path("credentials/gmail_client_secret.json").exists(),
        "Download OAuth client secret from Google Cloud Console"
    )

    # 10. Data directory
    Path("data").mkdir(exist_ok=True)
    check(
        "Data directory exists",
        Path("data").exists(),
        "Created automatically"
    )

    # 11. Credentials directory
    check(
        "Credentials directory exists",
        Path("credentials").exists(),
        "Create: mkdir credentials"
    )

    # Print results
    print(f"  {'CHECK':<45} {'STATUS':<8}")
    print(f"  {'-'*45} {'-'*8}")

    pass_count = 0
    fail_count = 0
    for name, status, fix in CHECKS:
        icon = "PASS" if status == "PASS" else "FAIL"
        print(f"  {name:<45} {icon}")
        if status == "PASS":
            pass_count += 1
        else:
            fail_count += 1

    print(f"\n  Results: {pass_count} passed, {fail_count} failed")

    if fail_count > 0:
        print(f"\n  Fixes needed:")
        print(f"  {'-'*55}")
        for name, status, fix in CHECKS:
            if status == "FAIL":
                print(f"    {name}:")
                print(f"      -> {fix}")
        print()

    if fail_count == 0:
        print("\n  All checks passed! Run: python main.py")
    else:
        print(f"\n  Fix the {fail_count} issue(s) above, then run this again.")

    print()


if __name__ == "__main__":
    main()
