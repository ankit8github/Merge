"""Owner-run masked password entry; exclusively creates ignored backend/.env."""
import getpass
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    target = ROOT / "backend" / ".env"
    if not sys.stdin.isatty():
        raise SystemExit("Run directly in your local interactive terminal; no piped passwords.")
    if target.exists():
        raise SystemExit("backend/.env already exists. Stop and review locally; nothing overwritten.")
    ignored = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "check-ignore", "--quiet", "backend/.env"],
        cwd=ROOT,
        check=False,
    )
    if ignored.returncode != 0:
        raise SystemExit("Cannot confirm backend/.env is gitignored. Stop.")
    password = getpass.getpass("New merge_app password (not the administrator password): ")
    confirmation = getpass.getpass("Confirm merge_app password: ")
    if not password or password != confirmation:
        raise SystemExit("Empty or mismatched password. Nothing written.")
    if "${" in password or any(ord(char) < 32 for char in password):
        raise SystemExit("Use a single-line password without ${ interpolation syntax. Nothing written.")
    # JSON double quoting matches dotenv escaping; preserve Unicode literally.
    contents = (
        "MERGE_DB_HOST=127.0.0.1\nMERGE_DB_PORT=5432\n"
        "MERGE_DB_NAME=merge_dev\nMERGE_DB_USER=merge_app\n"
        f"MERGE_DB_PASSWORD={json.dumps(password, ensure_ascii=False)}\n"
    )
    with target.open("x", encoding="utf-8", newline="\n") as output:
        output.write(contents)
    print("Created ignored backend/.env. No credentials printed.")


if __name__ == "__main__":
    main()
