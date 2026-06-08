# Langfuse Observability Plugin

This plugin ships bundled with Ares but is **opt-in** — it only loads when
you explicitly enable it.

## Enable

Pick one:

```bash
# Interactive: walks you through credentials + SDK install + enable
ares tools  # → Langfuse Observability

# Manual
pip install langfuse
ares plugins enable observability/langfuse
```

## Required credentials

Set these in `~/.ares/.env` (or via `ares tools`):

```bash
ARES_LANGFUSE_PUBLIC_KEY=pk-lf-...
ARES_LANGFUSE_SECRET_KEY=sk-lf-...
ARES_LANGFUSE_BASE_URL=https://cloud.langfuse.com   # or your self-hosted URL
```

Without the SDK or credentials the hooks no-op silently — the plugin fails
open.

## Verify

```bash
ares plugins list                 # observability/langfuse should show "enabled"
ares chat -q "hello"              # then check Langfuse for a "Ares turn" trace
```

## Optional tuning

```bash
ARES_LANGFUSE_ENV=production       # environment tag
ARES_LANGFUSE_RELEASE=v1.0.0       # release tag
ARES_LANGFUSE_SAMPLE_RATE=0.5      # sample 50% of traces
ARES_LANGFUSE_MAX_CHARS=12000      # max chars per field (default: 12000)
ARES_LANGFUSE_DEBUG=true           # verbose plugin logging
```

## Disable

```bash
ares plugins disable observability/langfuse
```
