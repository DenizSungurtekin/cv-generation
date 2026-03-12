import importlib.util
import json
import sys
from pathlib import Path

import anthropic
import questionary
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent


# ─────────────────────────────────────────────
# Tool definitions (what Claude can call)
# ─────────────────────────────────────────────

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the text content of a file. Paths are relative to the project root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative or absolute path to the file"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List all files inside a directory. Paths are relative to the project root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Relative or absolute path to the directory"}
            },
            "required": ["directory"],
        },
    },
    {
        "name": "render_pdfs",
        "description": (
            "Render cv.pdf and cover.pdf for one language using structured data. "
            "Call this twice: once for 'fr' and once for 'en'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lang": {
                    "type": "string",
                    "enum": ["fr", "en"],
                    "description": "Language for this render pass",
                },
                "cv_data": {
                    "type": "object",
                    "description": "Structured CV data tailored to the job and written in the target language",
                    "properties": {
                        "name":           {"type": "string"},
                        "title":          {"type": "string"},
                        "contact": {
                            "type": "object",
                            "properties": {
                                "email":    {"type": "string"},
                                "phone":    {"type": "string"},
                                "location": {"type": "string"},
                                "linkedin": {"type": "string"},
                                "github":   {"type": "string"},
                                "website":  {"type": "string"},
                            },
                        },
                        "summary":        {"type": "string"},
                        "experience":     {"type": "array"},
                        "education":      {"type": "array"},
                        "skills":         {"type": "array"},
                        "languages":      {"type": "array"},
                        "certifications": {"type": "array"},
                    },
                    "required": ["name", "title", "contact", "summary", "experience", "education", "skills", "languages"],
                },
                "cover_data": {
                    "type": "object",
                    "description": "Cover letter data tailored to the job and written in the target language",
                    "properties": {
                        "date":       {"type": "string"},
                        "company":    {"type": "string"},
                        "position":   {"type": "string"},
                        "greeting":   {"type": "string"},
                        "paragraphs": {"type": "array", "items": {"type": "string"}},
                        "closing":    {"type": "string"},
                        "signature":  {"type": "string"},
                    },
                    "required": ["date", "company", "position", "greeting", "paragraphs", "closing", "signature"],
                },
            },
            "required": ["lang", "cv_data", "cover_data"],
        },
    },
]


# ─────────────────────────────────────────────
# Tool execution (runs locally when Claude calls a tool)
# ─────────────────────────────────────────────

def execute_tool(name: str, inputs: dict, job_name: str, template_name: str) -> str:
    if name == "read_file":
        path = Path(inputs["path"])
        if not path.is_absolute():
            path = BASE_DIR / path
        if not path.exists():
            return f"Error: file not found — {path}"
        return path.read_text(encoding="utf-8")

    elif name == "list_files":
        directory = Path(inputs["directory"])
        if not directory.is_absolute():
            directory = BASE_DIR / directory
        if not directory.exists():
            return f"Error: directory not found — {directory}"
        files = [str(f.relative_to(BASE_DIR)) for f in sorted(directory.iterdir()) if f.is_file()]
        return json.dumps(files)

    elif name == "render_pdfs":
        lang        = inputs["lang"]
        cv_data     = inputs["cv_data"]
        cover_data  = inputs["cover_data"]
        template_dir = BASE_DIR / "templates" / template_name

        # Find profile photo in the user directory (first image found)
        user_name = cv_data["name"].lower().split()[0]  # fallback heuristic
        photo_path = None
        for user_dir in (BASE_DIR / "users_info").iterdir():
            if user_dir.is_dir():
                for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
                    matches = list(user_dir.glob(ext))
                    if matches:
                        photo_path = matches[0]
                        break

        # Load and call template renderer
        spec = importlib.util.spec_from_file_location("template_main", template_dir / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        output_dir = BASE_DIR / "generated" / job_name / lang
        output_dir.mkdir(parents=True, exist_ok=True)

        module.render(
            cv_data=cv_data,
            cover_data=cover_data,
            photo_path=photo_path,
            output_dir=output_dir,
            lang=lang,
            template_dir=template_dir,
        )
        return f"✓ PDFs saved to generated/{job_name}/{lang}/cv.pdf and cover.pdf"

    return f"Error: unknown tool '{name}'"


# ─────────────────────────────────────────────
# Agentic loop
# ─────────────────────────────────────────────

def run_agent(user: str, job: str, template: str):
    client = anthropic.Anthropic()

    system_prompt = f"""You are an expert CV and cover letter writer acting as an autonomous agent.

Your goal: generate a tailored CV and cover letter in both French AND English for user '{user}' applying to job '{job}'.

Project root: {BASE_DIR}

Step-by-step workflow:
1. Read the user profile: users_info/{user}/profile.md
2. Read the job description: job_descriptions/{job}.md
3. Call list_files on users_info/{user}/ to detect the profile photo filename
4. For French ('fr'): craft tailored cv_data and cover_data entirely in French, then call render_pdfs
5. For English ('en'): craft tailored cv_data and cover_data entirely in English, then call render_pdfs
6. When both renders are done, summarise the output paths to the user

Rules:
- Tailor every bullet point and summary to match the job description
- Keep all text in the target language (no mixing)
- certifications may be an empty list if none exist
- contact fields may be empty strings if not available in the profile"""

    messages = [
        {"role": "user", "content": f"Generate CV and cover letter for user='{user}', job='{job}', template='{template}'."}
    ]

    print(f"\nAgent starting — user={user}, job={job}, template={template}\n")

    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=8096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        # Collect any text Claude outputs along the way
        for block in response.content:
            if hasattr(block, "text") and block.text:
                print(block.text)

        if response.stop_reason == "tool_use":
            # Append Claude's response to the conversation
            messages.append({"role": "assistant", "content": response.content})

            # Execute every tool Claude requested and collect results
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  → tool: {block.name}({json.dumps(block.input, ensure_ascii=False)[:120]})")
                    result = execute_tool(block.name, block.input, job, template)
                    print(f"    ← {result[:100]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Return results to Claude
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            break
        else:
            print(f"Unexpected stop reason: {response.stop_reason}")
            break

    print("\nDone.")


# ─────────────────────────────────────────────
# Interactive selection
# ─────────────────────────────────────────────

def pick(label: str, choices: list[str]) -> str:
    if not choices:
        print(f"No {label} found. Aborting.")
        sys.exit(1)
    result = questionary.select(label, choices=choices).ask()
    if result is None:          # user pressed Ctrl-C
        sys.exit(0)
    return result


def interactive_select() -> tuple[str, str, str]:
    print()

    # ── Users ──────────────────────────────────
    users = sorted(
        d.name for d in (BASE_DIR / "users_info").iterdir() if d.is_dir()
    )
    user = pick("Select user:", users)

    # ── Profile check ──────────────────────────
    profile_path = BASE_DIR / "users_info" / user / "profile.md"
    if not profile_path.exists():
        print(f"\n  ⚠  No profile.md found for '{user}'.")
        print(f"     Run /gen_personal_info_cv --user {user} to generate it, or create it manually.")
        print(f"     Path: {profile_path}\n")
        sys.exit(1)

    # ── Jobs ───────────────────────────────────
    jobs = sorted(
        f.stem for f in (BASE_DIR / "job_descriptions").iterdir() if f.suffix == ".md"
    )
    job = pick("Select job description:", jobs)

    # ── Templates ──────────────────────────────
    templates = sorted(
        d.name for d in (BASE_DIR / "templates").iterdir() if d.is_dir()
    )
    template = pick("Select template:", templates)

    print()
    return user, job, template


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def main():
    user, job, template = interactive_select()
    run_agent(user, job, template)


if __name__ == "__main__":
    main()
