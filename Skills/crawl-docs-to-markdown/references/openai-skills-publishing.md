# OpenAI Skills Publishing Notes

Use this file when packaging or publishing the skill to OpenAI-hosted environments.

## Official constraints

Source: OpenAI Skills guide.

- A skill is a bundle of files plus a `SKILL.md` manifest.
- A zip upload must contain a single top-level folder.
- Exactly one `skill.md` or `SKILL.md` file is allowed in a skill bundle.
- Maximum zip upload size is 50 MB.
- Maximum file count per skill version is 500.
- Maximum uncompressed file size is 25 MB.

Official docs:

- https://developers.openai.com/api/docs/guides/tools-skills

Relevant sections:

- Create a skill: directory upload and zip upload
- Skills in the user prompt
- Limits and validation
- Inline skills
- Risks and safety

## Local shell usage

For local shell usage, the environment passes:

- `name`
- `description`
- `path`

The model uses that metadata to decide whether to invoke the skill, then reads `SKILL.md` from `path`.

## Hosted skill zip upload

OpenAI documents zip upload as:

```bash
curl -X POST 'https://api.openai.com/v1/skills' \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F 'files=@./basic_math.zip;type=application/zip'
```

This skill includes `scripts/package_skill.py` to create that zip bundle correctly.

## Inline skill source

OpenAI also supports inline skill bundles by base64-encoding the zip and placing it in `skills[].source` with:

- `type: "base64"`
- `media_type: "application/zip"`

This skill's packaging script can emit a ready-to-use inline JSON fragment.

## Safety

Treat any skill as privileged instructions and code. OpenAI explicitly warns that skills can influence planning, tool usage, and command execution, and should be reviewed before use.
