# References: historical specs and UI documentation

- `legacy_specs/`: **full original** high-level project specs for four repos plus product overview (dated ~October 9, 2026). They **contain superseded RabbitMQ** assumptions for Main ↔ AI and the earlier claim that MCP Server is always Backend-owned. Treat them as history, not as executable architecture instructions.
- `frontend_ui/`: detailed screen and interactions specs for Figma concept B. These describe users' desired screens; verify wire payloads against `../contracts/`.

For newest team decisions, always see `../04_DECISIONS_AND_CONFLICTS.md`. This bundle intentionally stores the originals unmodified to preserve provenance and avoid silently rewriting historical requirements.
