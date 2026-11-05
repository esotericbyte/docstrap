# Pitch 0002 — Pitchhouse

## 6. Architecture & Tradeoffs

**Markdown round-trip:**
- *Chosen:* Yes — exporter is MVP scope.

## 7. Open Questions

- [ ] **Q1.** Name: "Pitchhouse"? "Hatchpad"? "Hatchery Hub"? Something else? Locks package names.
- [ ] **Q2.** SurrealDB really? Or fall back to Postgres + JSONB?
- [x] **Q3.** Auth: single static token / OIDC / both? Affects deploy story.
- [ ] **Q4.** Where does the SvelteKit app live? `apps/pitchhouse-web/` is proposed; needs blessing.

## 8. Risks

Nothing here is numbered.
