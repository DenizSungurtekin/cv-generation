import argparse
import base64
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
IMAGE_MIMES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def find_cv_file(user_dir: Path) -> Path | None:
    """Find the first PDF or image file that is not profile.md."""
    for ext in ["*.pdf", "*.jpg", "*.jpeg", "*.png", "*.webp"]:
        matches = [f for f in user_dir.glob(ext) if f.stem != "profile"]
        if matches:
            return matches[0]
    return None


def build_message_content(cv_file: Path) -> list:
    suffix = cv_file.suffix.lower()
    raw = base64.standard_b64encode(cv_file.read_bytes()).decode()

    if suffix == ".pdf":
        file_block = {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": raw},
        }
    elif suffix in IMAGE_EXTS:
        file_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": IMAGE_MIMES[suffix], "data": raw},
        }
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    prompt = """Extract ALL information from this CV and produce a profile.md file using exactly this structure.
Keep every detail (dates, company names, achievements, technologies, etc.).
If a field is absent from the CV, leave its value empty but keep the heading.
Output ONLY the raw markdown — no explanation, no code fences.

---

# Personal Profile — [Full Name]

## Personal Information
- **Full Name:**
- **Email:**
- **Phone:**
- **Location:**
- **LinkedIn:**
- **GitHub:**
- **Website:**

## Professional Summary
[2-3 sentence summary extracted or inferred from the CV]

## Work Experience

### [Job Title] — [Company Name] | [City, Country] | [Start Month YYYY] – [End Month YYYY or Present]
- [Achievement or responsibility]
- [Achievement or responsibility]
- [Achievement or responsibility]

(repeat for each position)

## Education

### [Degree] — [School Name] | [City, Country] | [Start YYYY] – [End YYYY]
[Optional details, honours, GPA, etc.]

(repeat for each entry)

## Skills

### [Category, e.g. Programming Languages]
[skill1], [skill2], [skill3]

(repeat for each category)

## Languages
- [Language]: [Level — Native / Fluent / Professional / Conversational]

## Certifications
- [Certification Name] — [Issuer] ([Year])

(omit section if none)"""

    return [file_block, {"type": "text", "text": prompt}]


def main():
    parser = argparse.ArgumentParser(description="Generate profile.md from an existing CV file (PDF or image)")
    parser.add_argument("--user", required=True, help="User folder name under users_info/  (e.g. deniz)")
    args = parser.parse_args()

    user_dir = BASE_DIR / "users_info" / args.user
    if not user_dir.exists():
        print(f"Error: user folder not found — {user_dir}")
        sys.exit(1)

    cv_file = find_cv_file(user_dir)
    if not cv_file:
        print(f"No CV file (PDF or image) found in {user_dir}")
        print("Add your existing CV as a PDF or image to that folder, then re-run.")
        sys.exit(1)

    print(f"CV file found: {cv_file.name}")

    profile_path = user_dir / "profile.md"
    if profile_path.exists():
        print("profile.md already exists — it will be overwritten with extracted data.")

    print("Sending CV to Claude for extraction...")
    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": build_message_content(cv_file)}],
    )

    profile_md = response.content[0].text.strip()
    profile_path.write_text(profile_md, encoding="utf-8")
    print(f"✓ profile.md written to {profile_path}")
    print("\n--- Preview (first 20 lines) ---")
    print("\n".join(profile_md.splitlines()[:20]))


if __name__ == "__main__":
    main()
