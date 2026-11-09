# ADR-0014: Configuration, secrets and environment shim

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
Settings, source definitions and secrets must be editable without code changes, must not be committed, and the DSH Python environment needs a temp-directory workaround for pip.

## Decision
Keep `config/settings.yaml` (runtime knobs), `config/sources.yaml` (channels) and prompt files under `config/`. Secrets live in `.env` (gitignored) or environment variables, with a local `ds_key.txt` fallback for DeepSeek. `tools/sitecustomize.py` forces mode 0777 on mkdir to work around a restrictive DACL in the sandboxed CPython.

## Rationale
Separates deploy-time configuration from code, protects keys, and documents the only environment workaround needed to install dependencies.

## Consequences (Costs)
`.env` parsing is intentionally minimal; the shim is environment-specific and must not be imported in production runs (it is only used on PYTHONPATH for pip installs).

## Code locations (traceability)
- `src/newsagent/config.py :: load_config, Config.secret`
- `src/newsagent/keys.py :: read_key_values, ensure_key_file` (first-run keys.txt bootstrap)
- `config/keys.example.txt` (empty template; real `keys.txt` is git-ignored)
- `config/settings.yaml, config/sources.yaml, .env.example`
- `tools/sitecustomize.py`
