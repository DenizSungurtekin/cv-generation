"""
Reusable CV/cover letter renderer.
Reads structured cv_data + cover_data from a JSON file and renders PDFs via the chosen template.

Usage:
  python render_cv.py --input /path/to/data.json --job <job_name> --template <template_name>

The JSON file must contain:
  {
    "fr": { "cv_data": {...}, "cover_data": {...} },
    "en": { "cv_data": {...}, "cover_data": {...} }
  }

Output: generated/<job>/<template>/{fr,en}/cv.pdf and cover.pdf
"""
import argparse
import importlib.util
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent

parser = argparse.ArgumentParser()
parser.add_argument("--input",    required=True, help="Path to JSON file with fr/en cv_data and cover_data")
parser.add_argument("--job",      required=True, help="Job name (used for output folder)")
parser.add_argument("--template", required=True, help="Template folder name under templates/")
parser.add_argument("--user",     required=True, help="User folder name under users_info/")
args = parser.parse_args()

# Load template renderer
template_dir = BASE_DIR / "templates" / args.template
spec   = importlib.util.spec_from_file_location("template_main", template_dir / "main.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Find profile photo
photo_path = None
user_dir = BASE_DIR / "users_info" / args.user
for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
    matches = list(user_dir.glob(ext))
    if matches:
        photo_path = matches[0]
        break

# Load data
data = json.loads(Path(args.input).read_text(encoding="utf-8"))

# Render each language
for lang in ("fr", "en"):
    if lang not in data:
        print(f"  Skipping {lang} (not in JSON)")
        continue

    cv_data    = data[lang]["cv_data"]
    cover_data = data[lang]["cover_data"]
    output_dir = BASE_DIR / "generated" / args.job / args.template / lang
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Rendering {lang.upper()}...")
    module.render(
        cv_data=cv_data,
        cover_data=cover_data,
        photo_path=photo_path,
        output_dir=output_dir,
        lang=lang,
        template_dir=template_dir,
    )
    print(f"  generated/{args.job}/{args.template}/{lang}/cv.pdf")
    print(f"  generated/{args.job}/{args.template}/{lang}/cover.pdf")

print("\nDone.")
