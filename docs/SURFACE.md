# The product surface: MCP server, local app, public site

*Designed 2026-10-06 (A33), built in slices 15 and 17. Written before the
code so the agent (slice 14) is built to serve it.*

Three surfaces, one rule above all: **Riot's text stays on the user's
machine.** Anything public shows only this project's own content: what it
is, measured numbers, rule references, and how to install it.

```
 user's PC                                             public internet
 ┌──────────────────────────────────────────┐          ┌──────────────────────┐
 │ Claude Desktop ──stdio──► MCP server     │          │ Static site (Vercel) │
 │                            │             │          │  what it is          │
 │ Browser ──localhost──► local web app     │          │  measured results    │
 │                            │             │          │  install + connect   │
 │                     agent / retrieval    │          │  NO Riot text        │
 │                     Postgres + Ollama    │          └──────────────────────┘
 └──────────────────────────────────────────┘
```

## 1. MCP server (slice 15), local only

Started by the MCP client over **stdio** (Claude Desktop launches it as a
subprocess). No network listener, so nothing is exposed and no rule text
leaves the machine. Built with the MCP Python SDK.

| Tool | Input | Output | Available from |
|---|---|---|---|
| `search_rules` | `question`, `as_of` (date, default today), `k` (default 5) | passages: ref (`core@1.4:419.4.a`), version, valid from/to, text | now (slice 6 retrieval, best configuration at the time) |
| `ask` | `question`, `as_of` | answer, citations (version-qualified refs), confidence score, sources | slice 14 (agent) |
| `what_changed` | `rule` ref or `topic`, `from_version`, `to_version` | aligned rules with a word-level diff | now (`make diff` code, text alignment, A15) |
| `get_rule` | `ref` (`core@1.4:419.4.a`) | exact rule text, version, valid from/to | now |
| `list_versions` | none | versions with printed and effective dates, basis (stated or announcement, A17) | now |

Every output carries version and validity dates, so the calling model can
never present an outdated rule as current without the evidence in front of
it. Errors are explicit: an unknown ref, a date before the first datable
version (v1.0 is refused, A16), or an unreachable database each return a
named error, never an empty result that looks like "no such rule".

**Prompt injection (slice 16) applies here first.** Rule and card text is
imperative ("Target player discards"); tool outputs keep it inside clearly
delimited fields, as the answer prompt already does.

## 2. Local web app (slice 17), TypeScript

Vite + React + TypeScript, served on `localhost`, talking to a thin local
HTTP API over the same functions the MCP server calls. Screens:

- **Ask:** question, an "as of" date picker (default today), the answer with
  inline citations and a confidence badge (A21, once calibrated).
- **Sources:** each cited passage with its version, validity window, and a
  mark when a newer version exists.
- **What changed:** pick a rule or topic and two versions, see the diff.
- **Versions:** the timeline of rules versions and effective dates.

## 3. Public site on Vercel (with slice 17)

Static, built from a `site/` folder with the same TypeScript tooling, and
deployed by Vercel from this repository. No server code, no models, no Riot
text. Pages:

- **What it is:** the problem (rules change; naive search answers with
  outdated rules), with the slice 3 capture described by rule references.
- **Results:** recall@k with Wilson intervals per stratum, the ablation table
  (naive, as-of, embedders, hybrid, rerank), and every prediction against
  its result, misses included. Read from a committed numbers-only summary
  exported from `evals/runs/`, never typed in by hand (brief: split write
  from read).
- **Install and connect:** prerequisites, setup commands, and the Claude
  Desktop configuration snippet for the local MCP server.
- **Credits and licences:** CC BY-SA 4.0 attribution for the rulings
  (Christian "Near" Ivicevic), and Riot's position on fan tools once the
  legal pages are read.

**Gate:** before the site goes public, the user reads Riot's Legal Jibber
Jabber, developer policy and Digital Tools Policy (deferred since slice 1),
and the site follows them. Vercel's free Hobby plan is for personal,
non-commercial projects; this one is both.
