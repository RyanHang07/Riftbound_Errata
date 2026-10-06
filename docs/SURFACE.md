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

Modelled on **ui.shadcn.com**: a landing page, a docs section with a left
sidebar, and a top nav bar with GitHub stats at the right. Static, built
from a `site/` folder and deployed by Vercel from this repository. No server
code, no models, no Riot text.

**Stack.** Next.js (static export) + Tailwind CSS + shadcn/ui components,
with docs pages written in MDX, the same pattern shadcn's own site uses. The
local app (section 2) uses Tailwind and shadcn/ui too, so both look like one
product. Light and dark themes, with a toggle.

**Nav bar (every page).**

```
┌───────────────────────────────────────────────────────────────────────────┐
│ ◆ rb_errata   Docs  Results  Changelog         [Search ⌘K]  ★ 123  ◐      │
└───────────────────────────────────────────────────────────────────────────┘
```

- Left: project name and mark, then Docs, Results, Changelog.
- Right: docs search (⌘K command palette, shadcn's pattern), the **GitHub
  button with the star count**, and the theme toggle.
- **On small screens the doc shortcuts win.** Below about 860px the GitHub
  button is hidden and search shrinks to an icon, so Docs and Changelog
  stay visible; below about 520px the name collapses to the logo; Results
  is the last link to go (below about 380px), since the landing links to it.
- **GitHub stats are fetched at build time** from the public GitHub API and
  baked into the page, refreshed on every deploy (and by a scheduled
  rebuild). Not fetched in the visitor's browser: GitHub's unauthenticated
  limit is 60 requests an hour per visitor IP, and a failed fetch would show
  a broken number. If the build-time fetch fails, the button shows without a
  count rather than a wrong one. Requires the repository to be public.

**Landing page (`/`).**

- Hero: one line on the problem ("Rules change. Search engines don't
  notice."), one on the answer (rules answered as of a date, with versioned
  citations), and two buttons: **Get started** (to the docs) and **GitHub**.
- The headline result, as numbers with intervals: the naive search versus
  the date-aware one, from the committed runs.
- Three feature cards: version-aware search, the MCP tools, everything runs
  locally and offline.
- A short "how it works" strip: question and date in, the rules in force on
  that date, an answer citing `core@1.4:419.4.a` style references.

**Docs (`/docs/...`), left sidebar, "On this page" outline on the right.**

| Section | Pages |
|---|---|
| Getting started | Introduction · Installation · Quick start |
| Connect | Claude Desktop (MCP config snippet) · Local web app |
| Tools reference | `search_rules` · `ask` · `what_changed` · `get_rule` · `list_versions`: each with inputs, outputs, an example and its errors |
| How it works | Rules versions and effective dates · Why naive search fails · Retrieval pipeline (date filter, embedder, reranker) · Confidence score |
| Evaluation | The question set and its review · recall@k and Wilson intervals · Predictions vs results, misses included |
| Reference | Configuration and pins · Make targets · FAQ · Credits and licences |

Each page ends with previous/next links, as shadcn's do. Examples in the
docs use rule references and paraphrase, never Riot's rule text.

**Results (`/results`).** The ablation table (naive, as-of, embedders,
hybrid, rerank) with recall@k, Wilson intervals and paired McNemar results,
and each prediction next to its outcome. Read from a committed numbers-only
summary exported from `evals/runs/`, never typed in by hand (brief: split
write from read).

**Gate.** Before the site goes public, the user reads Riot's Legal Jibber
Jabber, developer policy and Digital Tools Policy (deferred since slice 1),
and the site follows them; the credits page then states Riot's position on
fan tools alongside the CC BY-SA 4.0 attribution for the rulings
(Christian "Near" Ivicevic). Vercel's free Hobby plan is for personal,
non-commercial projects; this one is both.

## 4. Visual direction: inspired by Riftbound, never imitating it (A35)

**What Riftbound's look is built from** (sources below; the official site and
wiki were unreachable from the cloud session, so this rests on search
summaries of them and on secondary guides):
- Six domain colours in opposing pairs: Fury red / Calm green, Mind blue /
  Body orange, Chaos purple / Order yellow.
- Frame metal and gem shape mark rarity: bronze and round (common), silver
  and triangular (uncommon), gold and square (rare), minimalist gold, foil
  and pentagonal (epic).
- Premium finishes: cold foil and spot UV on overnumbered cards, gold-foil
  artist signatures on the rarest.
- A portal symbol at the heart of the logo, the "O" of the wordmark (Studio
  Moross with Marianna Oršho).

**What the site borrows, each with a meaning:**
- **Hero, always dark:** two rows of tilted cards drift in opposite
  directions behind the text. Each card is one of *our* version-change
  questions with its "as of" date and the rule reference it resolves to; a
  domain-hue edge glow and a bronze, silver or gold frame. Pauses on hover.
- **Version-flip card:** one gold-framed card flips between "v1.3: no" and
  "v1.4: yes" for the Legion question, the changed term highlighted. The
  project's thesis in five seconds. Paraphrase only. Pausable.
- **Foil:** a light sweep on hover; cursor tilt and a holo shimmer only on
  the featured card, as foil is reserved for rare cards.
- **Section hues in docs:** Getting started Calm green, Connect Body orange,
  Tools Mind blue, How it works Chaos purple, Evaluation Order yellow,
  Reference silver. Fury red is reserved for "outdated rule".
- **Metal tiers on Results:** bronze edge for the baseline, silver for
  configurations kept, gold for the current best. Rank, as in the game.
- **Reduced motion:** carousel still, card flips only on a button, no
  sheen or tilt.

**Never used:** Riot's logo or portal symbol, real card frames, domain
symbols, card art, or anything that could pass for an official Riot page.
The footer states the site is an unofficial fan project.

Sources:
- [Riftbound domains (League of Legends wiki)](https://wiki.leagueoflegends.com/en-us/Riftbound:Domain)
- [Domain 101: the six domains (riftbound.gg)](https://riftbound.gg/domain-101-understanding-the-five-domains-of-riftbound/)
- [Riftbound rarity guide (Eneba)](https://www.eneba.com/hub/collectibles/riftbound-rarity-guide/)
- [Riftbound rarities explained (Card Gamer)](https://cardgamer.com/guides/riftbound-card-rarities/)
- [Collectability in Riftbound: Origins (official)](https://playriftbound.com/en-us/news/announcements/collectability-in-riftbound-origins/)
- [Riftbound logo design (Studio Moross)](https://www.studiomoross.com/work/riftbound-logo-design)
- [Riftbound branding (Marianna Oršho)](https://www.marianna-orsho.com/branding/riotgames-riftbound)
- [Riftbound TCG is a visual masterpiece (Artiholics)](https://artiholics.com/riftbound-tcg-visual-masterpiece/)
