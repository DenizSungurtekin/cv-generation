---
name: cv-generation
description: Interactively generate tailored CV and cover letter PDFs (French + English). Lists available users, jobs, and templates with arrow-key selection.
user-invocable: true
allowed-tools: Bash, Read, Write, Glob
---

You are the CV generation agent. Do NOT run agent.py. Instead, follow these steps directly:

## Step 1 — List available options

Run these commands to discover what's available:
```bash
ls users_info/
find job_descriptions -name "*.md" | sed 's|job_descriptions/||;s|\.md||'
ls templates/
```

Display the results clearly and ask the user to select a user and job.
Do NOT ask for a template — PDFs will be generated for ALL available templates.
Wait for their answer before continuing.

## Step 2 — Check profile.md

Check if `users_info/<user>/profile.md` is non-empty.
If it is empty or missing, read the user's CV file (PDF or image in their folder) and fill profile.md with all extracted information using this structure:

```
# Personal Profile — [Full Name]
## Personal Information
## Professional Summary
## Work Experience
## Education
## Skills
## Languages
## Certifications (if any)
## Interests (if any)
```

Confirm to the user that profile.md is ready before continuing.

## Step 3 — Read source files

Read:
- `users_info/<user>/profile.md`
- `job_descriptions/<user>/<job>.md` (or `job_descriptions/<job>.md` if not user-scoped)

## Step 4 — Generate tailored content

Based on the profile and job description, craft tailored cv_data and cover_data in **both French and English**.
Rules:
- Every bullet point and the summary must be tailored to the job description
- Keep all text in the target language (no mixing)
- Use key `tags` (not `items`) inside each skills group
- `certifications` may be an empty list
- **Fill the full A4 page**: write rich, detailed content — longer summaries (3-4 sentences), 4-5 bullet points per role, add extra context from the profile (projects, achievements, awards). The CV and cover letter must look full and professional, not sparse. A half-empty page is unacceptable. Aim to fill ~90-95% of the page — do NOT overflow (content must stay on 1 page).
- **Cover letter**: aim for 4-5 substantial paragraphs that fill the page. Each paragraph should be 3-5 sentences.
- **Confirmed working CSS padding** (do not change in templates): `cv-sidebar: 14pt 12pt 14pt 14pt`, `cv-main: 14pt 16pt 14pt 16pt`.

Build a JSON object with this structure:
```json
{
  "fr": { "cv_data": { ... }, "cover_data": { ... } },
  "en": { "cv_data": { ... }, "cover_data": { ... } }
}
```

Write it to `generated/<job>/cv_input.json` (persist it for future re-renders).

## Step 5 — Render PDFs for ALL templates

Run the renderer once per available template (use the list from Step 1):

```bash
.venv/Scripts/python render_cv.py --input generated/<job>/cv_input.json --job <job> --template <template> --user <user>
```

Repeat for every template. Stream and display all output.

## Step 6 — Summary

Show the user all generated PDF paths grouped by template:
```
modern/  → generated/<job>/fr/cv.pdf, cover.pdf | en/cv.pdf, cover.pdf
classic/ → ...
sharp/   → ...
slate/   → ...
```
