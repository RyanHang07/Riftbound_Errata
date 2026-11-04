# Riot's policies against this project

*Read 2026-11-04 from text the user pasted (this session's network blocks
Riot's sites): Riot's "Legal Jibber Jabber" (shown "Last Updated: August
2018"), the Riftbound Developer API Policy, the General Developer Policies
("Last Updated: May 29, 2025") and the API Terms ("Last Updated: December 9,
2013"). This is a reading of the
policies against the project, not legal advice; quotes are Riot's wording.*

## What applies, clause by clause

| Clause | Riot's words | This project | Status |
|---|---|---|---|
| Licence (LJJ 1) | "a personal, non-exclusive, non-sublicenseable, non-transferable, revocable, limited license ... strictly for noncommercial ... community use" | Free, open source, no money involved | Fits. Revocable at any time. |
| No commercial projects (LJJ 2) | "You may not create commercial Projects, including any Project that crowdsources any portion of its funding ... or ... gate the content with a paywall" | No ads, paywall, crowdfunding or entity | Fits. Keep it that way. |
| Original content (LJJ 4) | "Don't steal other people's Projects; get their permission and give them credit." | Near's rulings used under CC BY-SA 4.0, credited on the site, README and question file | Fits. |
| Logos and trademarks (LJJ 5) | "you may not use any of our logos or trademarks anywhere in your Project ... You may not register domain names, social media accounts, or similar that uses Riot Games or any of our trademarks, trade names, character names" | No logos or card art anywhere. But the GitHub repository is named `Riftbound_Errata`, and "Riftbound" is a Riot trademark | **Done 2026-11-04 (A58):** repository renamed to `RB_Errata`, identifiers updated. Never use "Riftbound" in a domain, Vercel project or social account. Naming the game in descriptive text is what the required notice itself does. |
| Required notice (LJJ 6; Riftbound policy, Brand Integrity) | "[The title of your Project] was created under Riot Games' "Legal Jibber Jabber" policy using assets owned by Riot Games. Riot Games does not endorse or sponsor this project." ... "in a place that's clear and easy to find" | Was missing; the site had its own wording | **Done 2026-11-04**: verbatim on every site page, the local app, the README and the MCP server's instructions and `list_versions`; a test holds it verbatim. |
| No implied endorsement (Riftbound, Brand Integrity) | "You can't state or imply that you or your App are endorsed or sponsored by Riot" | Notice says so; the site's look borrows the League client's visual language | Fits. Keep the look from imitating Riot's own pages (the A33 rule: no Riot logos, card frames or domain symbols). |
| Registration (Riftbound) | "If your product serves players, you must register it with us regardless of whether or not your product uses official documented APIs." | The public site, MCP server and local app serve players | **Register on the Riot Developer Portal before the site is deployed or the project is promoted.** The user's action. |
| Apps and API key (LJJ 3) | "We prohibit the use of our IP in games and apps ... unless they have either a written license agreement from us or a valid Riot API key and comply with our API Terms and Policies" | The MCP server and local app are apps that use Riot's rules text | Registration (above) is the path to compliance; until then the tools stay on the user's own machine. |
| Use cases (Riftbound, App Policy) | Approved: "Deck builders", "Card libraries". Not approved: "Apps with a small, personal audience", "Apps that do not provide a link to a site or mockup", metagame data | A rules assistant is neither listed nor excluded; the public site is the required "link to a site" | Apply as a rules tool with a card library (slice 10); the site shows the user flow. Approval is Riot's call. |
| Cards (Riftbound, Implementation) | "Your App may only use Riftbound assets (including cards) provided by the Riot API. No external or unofficial materials." and "All Riftbound cards must display the official English text" | Slice 10 planned a card database | **Card text only from Riot's API**, never from the mirror's `card-catalog.json`, fan sites or scraping; display official English text; follow the API's rules for any card search. Needs the API key from registration. |
| Rules documents | (Not addressed directly; "No external or unofficial materials" names assets "including cards") | Rules PDFs come from Riot's CDN, verified by SHA-1; v1.3 exists only as a mirror copy (`mirror-only-unverified`) | Inferred: prefer Riot's own copies. v1.3 has no CDN copy under its hash; ask Riot (or find an official link) before shipping it to other users. |
| Game integrity (Riftbound) | "Products cannot create an unfair advantage for players" | A rules reference available to everyone; event rules on device use are separate | Fits, inferred. The docs should tell players to follow their event's rules on using devices during play. |
| Monetization, RSO, gameplay simulation (Riftbound) | Rules for monetized apps and for apps that "simulate or replicate Riftbound gameplay" | None of these | Not applicable. |
| AI and language models | Neither page mentions AI, machine learning or LLMs | Local model answers from Riot's rules text | Unknown until the general developer policies and the API Terms are read. |
| Riot's use of the project (LJJ 7) | "you agree that we may use, copy, modify, distribute, and make derivative works of your Project ... without having to credit you, pay you anything, or obtain your approval" | | Accepted by sharing the project. |

## General Developer Policies and API Terms

| Clause | Riot's words | This project | Status |
|---|---|---|---|
| Second required notice (General, Core Policies) | "[Your product] isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc." | Was missing | **Done 2026-11-04**, beside the first notice everywhere; tested. |
| Resemblance (General, Core Policies) | "Products cannot closely resemble Riot's games or products in style or function" | The site and local app are styled on the League client's "Hextech" visual language (palette, cut-corner frames, diamond markers; A39 to A40) | **Done 2026-11-04 (A58):** both restyled as an errata sheet; no gold frames, cut corners, diamonds, card shapes or domain hues. |
| Registration and audit (General) | "All products must be registered in, and audited by Riot Games through the Developer Portal" and "Any new features or changes to a product must be audited" | Not registered | **Register before deploying**; then each new feature (the agent, a card library) goes through the product's portal page. |
| Data sources (General) | "Products should use supported services from Riot Games for data ingestion" | Rules PDFs from Riot's CDN first, a fan mirror second; v1.3 mirror only | Inferred: drop the mirror for anything shipped to others; find an official source for v1.3 or leave it out of a public build. |
| Logos (General) | "Using Riot logos, trademarks etc. from the Press Kit must be limited to those cases where such use is inevitable" | None used | Fits. |
| Game integrity (General) | "Products should not remove game decisions" and no rank alternatives | A rules reference | Fits. |
| Ownership of API output (API Terms) | "Riot owns all right, title and interest ... in and to the Materials, including all output and executables of the Riot Games API, and including any modifications to or derivatives of the Materials" | Slice 10 would store card data from the API | Fits; card data stays Riot's. "Upon termination ... delete all of the Game Information in Your possession": the card store must be deletable in one step. |
| Passing API data on (API Terms; Riftbound App Policy) | "Using the Riot Games API to use, distribute or transmit the Game Information in any manner not authorized" and, not approved, "Apps with "middle-man" type of data usage, such as an app that obtains data from our API and gives or sells it to a third-party company" | The MCP server returns retrieved text to Claude Desktop, which sends it to Anthropic's servers | Inferred risk for slice 10: card text from the API should not flow to a cloud model without Riot's say-so. Ask in the registration; until answered, keep API card text to the local model and the local app. (The rules PDFs are not API data; they fall under Legal Jibber Jabber.) |
| Keys (API Terms; General) | "You may create only one (1) developer account"; "Do not include your API key in your code"; "A Development Key shall not be permitted to make more than ten (10) network calls every ten (10) seconds" | No key yet | When one exists: kept in `.env` (gitignored), never committed, rate-limited. |
| AI and language models | Not mentioned in any of the four documents | Local model answers; MCP to Claude Desktop | No clause found. The data-flow point above is the nearest one. |

## Gate status

- **Cleared:** keeping the project free and non-commercial; both required
  notices (done, tested); crediting Near's rulings; no logos.
- **Done 2026-11-04 (A58):** restyle of the site and local app; project
  identifiers and the GitHub repository renamed to `RB_Errata`.
- **Before the site is deployed or the project promoted:** register the product on the Riot Developer
  Portal (Riot audits it, and every new feature after).
- **Before slice 10 (card database):** an approved API key; card text only
  from Riot's API; ask Riot whether API card text may reach a cloud model
  through MCP, and keep it local until answered.
