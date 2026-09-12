# NagramiX product layer

This directory is the product source of truth for NagramiX. It defines **what** a feature means before `ios/` defines **how** it is integrated into official Telegram-iOS sources.

## Rules

1. Official Telegram-iOS is the only application code base.
2. NagramX and other clients are idea references only; their code is not compiled or copied.
3. Setting ids, defaults, semantics, privacy exclusions and acceptance criteria are defined here first.
4. Compilation proves build compatibility; iPhone device validation is tracked separately.

## Contents

- `PRODUCT.md` — identity and release model.
- `UPSTREAM_POLICY.md` — official Telegram-iOS pin policy.
- `SETTINGS.md` — canonical settings contract.
- `COMPATIBILITY.md` — iOS and IPA requirements.
- `features/registry.json` — machine-readable iOS implementation status.
- `features/README.md` — feature lifecycle.
- `releases/` — release scope and known limits.
