import base64
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS


def photo_to_data_uri(photo_path: Path) -> str | None:
    if not photo_path or not photo_path.exists():
        return None
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime = mime_map.get(photo_path.suffix.lower(), "image/jpeg")
    data = base64.b64encode(photo_path.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def render(cv_data: dict, cover_data: dict, photo_path: Path | None,
           output_dir: Path, lang: str, template_dir: Path):
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    photo_uri = photo_to_data_uri(photo_path) if photo_path else None
    css = CSS(filename=str(template_dir / "style.css"))

    # --- CV ---
    cv_html = env.get_template("cv.html.jinja2").render(cv=cv_data, photo_uri=photo_uri, lang=lang)
    HTML(string=cv_html, base_url=str(template_dir)).write_pdf(
        str(output_dir / "cv.pdf"), stylesheets=[css]
    )

    # --- Cover Letter ---
    cover_html = env.get_template("cover.html.jinja2").render(cover=cover_data, cv=cv_data, lang=lang)
    HTML(string=cover_html, base_url=str(template_dir)).write_pdf(
        str(output_dir / "cover.pdf"), stylesheets=[css]
    )
