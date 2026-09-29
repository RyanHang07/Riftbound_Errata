# Slice 1: corpus availability spike

*2026-09-29. The gate from brief section 6: is the corpus obtainable, and do
the rules documents carry dates? Nothing after this slice should be built
until this answer exists.*

## Verdict

**Proceed. The thesis survives, with two design consequences.**

| Brief section 6 outcome | Finding |
|:--|:--|
| Everything obtainable, dates present | **This one.** All five Core Rules versions are obtainable, and every one prints its date on page 1. |
| Cards yes, rules blocked | No. |
| Obtainable but undated | No, but the printed date is **not** the date a rule took effect (finding 3). |
| Corpus much smaller than 175k | No. Larger: about 410k tokens across all versions (finding 2). |

Consequences for later slices, both needing a decision before slice 2:

1. **Rule numbers are not stable between versions** (finding 4). A label such
   as `core:4.2.1` means different rules in different versions.
2. **Printed date and effective date differ by days** (finding 3). `valid_from`
   must come from the effective date, which lives in the patch-notes articles,
   not in the PDFs.

## How this was measured, and what could not be

The cloud session's network blocks every Riot and community host, including
for web fetches. Only web **search** and **GitHub** were reachable. So:

- Every claim about official pages below comes from a search result (title,
  URL and the search engine's snippet), not from opening the page. Each is
  listed in [Sources](#sources) so it can be checked.
- Every **count** (pages, tokens, rules, cards) was computed here from files
  obtained through GitHub, with the method stated.
- `scripts/spike1_check.sh` runs on the user's machine to record which
  official pages a home connection can reach. **Its result is still pending.**

Token counts use `tiktoken` with `cl100k_base`, as the brief specifies. The
project's models (nomic, qwen3) tokenize differently, so absolute numbers will
differ somewhat for them; relative sizes hold.

## Finding 1: the Core Rules history is obtainable, and provably Riot's

The GitHub repository `ChristianIvicevic/riftboundfaq` (an unofficial rulings
site, commit `816d3b3`, 2026-09-28) keeps every Core Rules and Tournament Rules
version in `sources/`.

**Provenance check.** Riot serves these PDFs from its Sanity CDN
(`cmsassets.rgpub.io`), which names each file after the SHA-1 of its bytes.
Search results exposed five official CDN URLs. Their filenames equal the SHA-1
of the GitHub copies, so those five are byte-for-byte Riot's files:

| File | SHA-1 | Matches an official CDN URL? |
|:--|:--|:--|
| CR-v1.0.pdf | `c780858c…` | not yet checked |
| CR-v1.1.pdf | `dbc96e31…` | not yet checked |
| CR-v1.2.pdf | `572377fc…` | **yes** [S1] |
| CR-v1.3.pdf | `7affc578…` | not yet checked |
| CR-v1.4.pdf | `e9ac8e3d…` | not yet checked |
| Tournament-Rules-2025-07-21.pdf | `1efc974a…` | **yes** [S2] |
| Tournament-Rules-2026-03-30.pdf | `d77651bc…` | **yes** [S3] |
| Tournament-Rules-2026-04-29.pdf | `e7086661…` | **yes** [S4] |
| Tournament-Rules-2026-07-16.pdf | `503da656…` | **yes** [S5] |

Part 1 of `scripts/spike1_check.sh` tests the remaining four the same way.

## Finding 2: size, counted

| Document | Versions | Pages | Tokens per version (cl100k) | Printed date |
|:--|:--|:--|:--|:--|
| Core Rules v1.0 "Pre-Origins" | 1 | 65 | 34,821 | 2025-06-02 |
| Core Rules v1.1 "Origins" | 1 | 70 | 46,419 | 2025-10-01 |
| Core Rules v1.2 "Spiritforged" | 1 | 82 | 51,535 | 2025-12-01 |
| Core Rules v1.3 "Unleashed" | 1 | 98 | 63,226 | 2026-03-30 |
| Core Rules v1.4 "Vendetta" | 1 | 120 | 81,053 | 2026-07-16 |
| Tournament Rules | 4 | 36-50 | 18,561 / 24,658 / 25,310 / 27,967 | 2025-07-21, 2026-03-30, 4/29/2026, 7/16/2026 |
| Card rules text, one per unique card | current only | | 31,085 to 36,282 (depends on dataset) | none |

Version names come from the repo's `sources/rules-manifest.json`.

| Total | Tokens |
|:--|:--|
| All Core Rules versions | 277,054 |
| All Tournament Rules versions | 96,496 |
| Cards (largest dataset) | 36,282 |
| **Everything counted** | **≈ 410,000** |
| Current snapshot only (CR v1.4 + TR 7/16 + cards) | ≈ 145,000 |

Not yet counted: patch notes, errata, FAQ and ban-list articles. They are web
pages, not PDFs, and could not be fetched from here.

**Against the brief's estimate.** `PLAN.md` estimated ~175k tokens. That is
close to the *current snapshot* (~145k), but the versioned corpus the thesis
needs is about 2.3x larger. The Core Rules alone grew 2.3x in 13 months.

**Method, and the correction it needed.** Text was extracted with `pypdf`,
which puts almost every word on its own line. Counting that raw text gave
inflated totals (CR v1.4: 139,249 tokens), because each line break is a token.
The table uses whitespace-normalised text (CR v1.4: 81,053). The raw figures
are kept in the working notes; the first report of them was wrong.

**Is retrieval justified?** Yes. The current Core Rules alone are 81k tokens,
ten times the 8,192-token context `doctor` uses, and at the measured CPU
prefill rate (37.7 tok/s, A14) reading them once would take about 36 minutes.

## Finding 3: dates exist, but the printed date is not the effective date

**Every PDF prints a date on page 1** (`Last Updated: …`). The PDF metadata is
useless for dating: creation and modification dates are empty in 4 of 5 Core
Rules files, and titles include internal names such as
`Flattened Copy of Riftbound Core Rules v1.2 Staging` and
`Riftbound Core Rules RUP3 Staging`.

**Formats are inconsistent**, even within one document series: Tournament
Rules use `2025-07-21` and `2026-03-30`, then `4/29/2026` and `7/16/2026`. A
date parser must handle both, and must refuse anything else rather than guess.

**The effective date differs from the printed date**, per search results:

| Version | Printed in PDF | Effective, per announcements |
|:--|:--|:--|
| CR v1.2 (Spiritforged) | 2025-12-01 | December 12, 2025 [S7] |
| CR v1.4 (Vendetta) | 2026-07-16 | July 24, 2026 [S8] [S9] |
| CR v1.1, v1.3 | 2025-10-01, 2026-03-30 | not established |

So `valid_from` must be the **effective** date, sourced from the patch-notes
articles, and `published_at` the printed one. The brief's schema already has
both columns, and this shows why both are needed. A question dated
2026-07-20 falls in the gap: v1.4 was published, but v1.3 was still the rule.

## Finding 4: rule numbers are not stable across versions

Rules were split on their numbers (`103.`, `103.2.`, `103.2.a.`) and compared
between consecutive versions. "Moved" means the exact same rule text
(over 40 characters) appears under a different number in the next version.

| Transition | Same number, same text | Same number, changed text | Exact text moved to a new number |
|:--|:--|:--|:--|
| v1.0 → v1.1 | 331 | 138 | 410 |
| v1.1 → v1.2 | 811 | 231 | 322 |
| v1.2 → v1.3 | 162 | 570 | 684 |
| v1.3 → v1.4 | 1,061 | 399 | 265 |

Examples that can be checked in the PDFs: `139` → `140` (v1.0 → v1.1),
`106.3.c` → `107.2.b` (v1.2 → v1.3), `112` → `111` and `108.7.d` → `108.7.e`
(v1.3 → v1.4).

**Caveat:** the parser is a heuristic. It finds 1,965 numbered rules in v1.4,
while one community site reports 2,216 [S10], so some rules are missed or
merged. The exact counts are approximate; renumbering at this scale is not in
doubt.

**Consequence.** Amendment A1 made a recall hit require the right `source_ref`
**and** the right version window. That still works, but only if `source_ref`
is read *within the version valid at the question's date*. It rules out
anything that joins versions on rule number, including the obvious way to
build `what_changed`. Aligning rules across versions needs text matching.
This is the design question to settle before slice 2.

## Finding 5: card data is obtainable, but only as of today

| Dataset | Rows | Unique names | Per set (OGN / OGS / SFD / UNL / VEN) | Stated source |
|:--|:--|:--|:--|:--|
| `riccjohn/riftbound-card-db` [S11] | 1,189 | 879 | 352 / 24 / 288 / 288 / 237 | Official card gallery, fetched 2026-09-28 |
| `gabezmcmillan/riftbound-ai` [S12] | 1,180 | 935 | 352 / 24 / 288 / 288 / 228 | RiftScribe community API |
| `ten-jin/tenjin-data-riftbound` [S13] | 948 | 940 | 298 / 24 / 224 / 227 / 175 | not stated |

- **Counts disagree** because the first two include alternate-art variants
  (`riftbound-ai` marks 160 rows as variants) and they treat names
  differently. Reconciling them is slice 2 work; none should be trusted alone.
- **Search results give printed set sizes** of Origins 298, Spiritforged 221,
  Unleashed 219, Vendetta 166 [S14]. Only `tenjin` is close to these.
- **None of the three records history.** Each holds current card text only.
  "Card text as of a date" needs the errata documents. The errata file in the
  rulings repo (63 cards, old and new text) has no dates either.
- **Useful bonus:** `tenjin` records ban dates (2026-03-31, 2026-07-24,
  2026-09-18), which match search results for Riot's announcements [S15].
- **The official source** is Riot's card gallery, which serves its data as
  JSON with no key, per `riccjohn`'s README.
- **The brief's "open-source rules engine"** was not identified with
  certainty. Candidates: `gabezmcmillan/riftbound-ai` (Python engine) and
  `ten-jin/tenjin-data-riftbound` (declarative rules). Neither is needed as
  ground truth, since card text is available directly.

## Finding 6: the rest of the official corpus, by search result

Not fetched; existence and dates are from search results only.

| Kind | Documents found | Dates (per search results) |
|:--|:--|:--|
| Patch notes | Origins, Spiritforged, Unleashed, Vendetta [S16] | Oct 2025; Dec 2025 (effective Dec 12); Mar 30, 2026; effective Jul 24, 2026 |
| Errata | Origins, Spiritforged, Unleashed, Vendetta [S17] | Oct 28, 2025 (plus 31 cards Dec 2025); Jan 14, 2026; 2026; Jul 2026 (8 cards) |
| FAQs | Origins, Spiritforged, Unleashed, Vendetta [S18] | not established |
| Ban lists | three waves [S15] | effective Mar 31, Jul 24 and Sep 18, 2026 |
| Official API | `riftbound-content-v1`, needs an approved key [S19] | lists "rulesets" among its assets; not examined |

This matches the brief's description of the corpus.

## Finding 7: legal terms (to read in full before any distribution)

What search results say; **the pages themselves must be read**:

- **Legal Jibber Jabber** [S20]: free fan projects are allowed. A shared
  project must carry the notice *"[Project] was created under Riot Games'
  'Legal Jibber Jabber' policy using assets owned by Riot Games. Riot Games
  does not endorse or sponsor this project."* It also grants Riot broad rights
  to use the project.
- **Riftbound developer policy** [S21]: Riot is "especially concerned with
  projects that enable Riftbound gameplay with automated rules, interactions,
  and resolutions." Card galleries and deck tools are encouraged. Card text
  must be the official English text. Using the official API needs a key or a
  written license. Monetisation needs registration and a free tier.
- **Riftbound Digital Tools Policy** announced by Riot [S22].

**Reading for this project:** a rules *reference* that cites official text
sits closer to the encouraged category than to automated gameplay, but that is
an interpretation, not a ruling. The repository already commits no Riot text
(brief section 7). The README's legal section should be completed once the
pages have been read.

## The brief's open questions 1-4

| # | Question | Answer |
|:--|:--|:--|
| 1 | Do the rules documents carry machine-readable dates? | **Yes, as printed text** on page 1, in two formats. Not in the metadata. And the printed date is not the effective date. |
| 2 | Is the open-source card JSON complete and current? | **Current, not complete in the useful sense:** three datasets disagree on counts, and none has history. |
| 3 | What do Riot's fan terms permit? | Free non-commercial projects with a notice; automated gameplay is the concern. **Needs a full read.** |
| 4 | Is the corpus really ~175k tokens? | **No: ~410k** across versions, ~145k for the current snapshot alone. |

## Still open

- Home-machine reachability of each official page (`spike1_check.sh`).
- CDN verification of Core Rules v1.0, v1.1, v1.3, v1.4.
- Effective dates of CR v1.1 and v1.3.
- Token counts of the article-based documents.
- A full read of the three legal pages.

## Sources

Official pages were **not opened**; the evidence is the search result for each
URL. GitHub repositories were cloned and read directly.

- [S1] Core Rules v1.2 on Riot's CDN: https://cmsassets.rgpub.io/sanity/files/dsfx7636/news_live/572377fcaa704a05f72eb42c104079d3b3bcf740.pdf
- [S2] Tournament Rules 2025-07-21: https://cmsassets.rgpub.io/sanity/files/dsfx7636/news_live/1efc974ac167eefd6e38a3e0364509741f785648.pdf
- [S3] Tournament Rules 2026-03-30: https://cmsassets.rgpub.io/sanity/files/dsfx7636/news_live/d77651bcaa7ca5a5b41a0ac0ea8112725a635680.pdf
- [S4] Tournament Rules 4/29/2026: https://cmsassets.rgpub.io/sanity/files/dsfx7636/news_live/e70866614d68a00a1cbd12c7de08124e0ea5e755.pdf
- [S5] Tournament Rules 7/16/2026: https://cmsassets.rgpub.io/sanity/files/dsfx7636/news_live/503da65669ced10598d62925a6f6bc15111af726.pdf
- [S6] Rulings repo with all rules PDFs: https://github.com/ChristianIvicevic/riftboundfaq (see `sources/`)
- [S7] Spiritforged patch notes: https://playriftbound.com/en-us/news/rules-and-releases/riftbound-core-rules-spiritforged-patch-notes/ and https://riftbound.gg/riftbound-core-rules-spiritforged-patch-notes/
- [S8] Vendetta patch notes: https://playriftbound.com/en-us/news/announcements/core-rules-vendetta-patch-notes/
- [S9] July 2026 Tournament Rules update: https://playriftbound.com/en-us/news/announcements/july-2026-tournament-rules-update-changelog/
- [S10] Rift Watcher rules page (2,216 rules in v2026-07-16): https://riftwatcher.com/rules/
- [S11] https://github.com/riccjohn/riftbound-card-db (commit `39b1217`, 2026-09-28)
- [S12] https://github.com/gabezmcmillan/riftbound-ai (commit `949f25b`, 2026-09-21)
- [S13] https://github.com/ten-jin/tenjin-data-riftbound (commit `12c37a0`, 2026-09-27)
- [S14] Set sizes and dates: https://articles.starcitygames.com/riftbound/riftbound-2026-set-release-schedule/ and https://riftcompare.com/guides/riftbound-sets-in-order
- [S15] Ban lists: https://playriftbound.com/en-us/news/announcements/july-ban-list-updates/ , https://playriftbound.com/en-us/news/announcements/september-ban-list-updates-effective-september-18-2026/ , https://riftbound.gg/riftbound-ban-announcement-march-31-2026/
- [S16] Patch notes index: https://playriftbound.com/en-us/news/rules-and-releases/riftbound-core-rules-patch-notes/ , https://playriftbound.com/en-us/news/rules-and-releases/riftbound-core-rules-unleashed-patch-notes/
- [S17] Errata: https://playriftbound.com/en-us/news/rules-and-releases/riftbound-origins-card-errata/ , https://playriftbound.com/en-us/news/rules-and-releases/riftbound-spiritforged-errata/ , https://playriftbound.com/en-us/news/rules-and-releases/unleashed-errata-updates/ , https://www.jaxon.gg/riot-riftbound-errata/ , https://riftbound.zone/en/guide/riftbound-errata-and-rulings/
- [S18] FAQs: https://playriftbound.com/en-us/news/rules-and-releases/riftbound-origins-faq/ , https://playriftbound.com/en-us/news/rules-and-releases/riftbound-spiritforged-faq/ , https://playriftbound.com/en-us/news/rules-and-releases/unleashed-rules-faq-and-clarifications/ , https://playriftbound.com/en-us/news/rules-and-releases/vendetta-rules-faq-and-clarifications/
- [S19] Riot Developer Portal, Riftbound: https://developer.riotgames.com/docs/riftbound and API list https://developer.riotgames.com/apis
- [S20] Legal Jibber Jabber: https://www.riotgames.com/en/legal
- [S21] Riftbound developer policy: https://developer.riotgames.com/policies/riftbound
- [S22] Digital Tools Policy announcement: https://x.com/playriftbound/status/1948792879201370296
- [S23] Rules Hub (index of all official documents): https://playriftbound.com/en-us/rules-hub/
- [S24] Banner "may no longer reflect Riftbound's rules": https://playriftbound.com/en-us/news/rules-and-releases/gameplay-guide-core-rules/
