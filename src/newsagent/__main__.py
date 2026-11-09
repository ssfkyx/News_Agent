# =============================================================================
# Module: newsagent.__main__
# Responsibilities: Entry point for `python -m newsagent`.
# Dependencies: newsagent.cli
# Dependents: CLI users
# ADRs: ADR-0001
# Traceability: docs/decisions/README.md
# =============================================================================
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
