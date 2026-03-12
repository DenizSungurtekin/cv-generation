---
name: gen_personal_info_cv
description: Generate or update a user's profile.md by extracting information from an existing CV file (PDF or image) in their users_info folder.
user-invocable: true
argument-hint: --user <name>
allowed-tools: Bash, Read
---

Run the profile extraction agent for the given user.

**Step 1 — check for a source CV file.**
Look inside `users_info/` for any PDF or image file for the user specified in $ARGUMENTS.
If none exists, tell the user:
> "No CV file found. Please drop your existing CV (PDF or image) into the user folder and run this command again."
Then stop.

**Step 2 — check for existing profile.md.**
If a `profile.md` already exists, show the user the first 15 lines and ask:
> "A profile.md already exists for this user. Do you want to overwrite it with data extracted from [filename]? (yes / no)"
If the user says no, stop.

**Step 3 — run extraction.**
```bash
.venv/Scripts/python gen_profile.py $ARGUMENTS
```

**Step 4 — show result.**
Read and display the generated `profile.md` to the user.
Ask: "Does this look correct? Would you like to edit anything?"
If the user wants changes, apply them directly to the file.
