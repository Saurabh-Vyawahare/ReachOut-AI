"""Setup Checker v3 (Dual API: OpenAI + Claude)"""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
CHECKS = []
def check(name, condition, fix):
    CHECKS.append((name, "PASS" if condition else "FAIL", fix))
def main():
    print("\n" + "="*60)
    print("  REACHOUT-AI v3 - SETUP CHECKER")
    print("="*60 + "\n")
    check(".env file exists", Path(".env").exists(), "Copy .env.example to .env")
    check("OpenAI API key set", bool(os.getenv("OPENAI_API_KEY")), "Add OPENAI_API_KEY to .env (platform.openai.com)")
    check("Anthropic API key set", bool(os.getenv("ANTHROPIC_API_KEY")), "Add ANTHROPIC_API_KEY to .env (console.anthropic.com)")
    check("Google Sheet ID set", bool(os.getenv("SPREADSHEET_ID")), "Add SPREADSHEET_ID to .env")
    gmail_count = sum(1 for i in range(1, 5) if os.getenv(f"GMAIL_{i}"))
    check(f"Gmail accounts ({gmail_count}/4)", gmail_count >= 1, "Add GMAIL_1-4 to .env")
    check("credentials/ exists", Path("credentials").exists(), "mkdir credentials")
    check("Sheets service account", Path("credentials/sheets_service_account.json").exists(), "Download from Google Cloud Console")
    check("Gmail OAuth secret", Path("credentials/gmail_client_secret.json").exists(), "Download from Google Cloud Console")
    Path("data").mkdir(exist_ok=True)
    check("data/ exists", Path("data").exists(), "Auto-created")
    check("src/ modules", Path("src/main.py").exists(), "src/ folder needed")
    print(f"  {'CHECK':<45} {'STATUS':<8}")
    print(f"  {'-'*45} {'-'*8}")
    p, f = 0, 0
    for name, status, fix in CHECKS:
        print(f"  {name:<45} {status}")
        if status == "PASS": p += 1
        else: f += 1
    print(f"\n  Results: {p} passed, {f} failed")
    if f:
        print(f"\n  Fixes:")
        for name, status, fix in CHECKS:
            if status == "FAIL": print(f"    {name}: {fix}")
    else:
        print("\n  All passed! Run: poetry run python src/main.py")
    print()
if __name__ == "__main__": main()
