// Docs navigation: one list drives the sidebar, the ⌘K menu, the pager and
// the static routes, so a page can never be in one and missing from another.
export type DocPage = { slug: string; title: string; lede: string; soon?: boolean };
export type DocGroup = { group: string; hue: string; pages: DocPage[] };

// Section hues are Riftbound's domain colours (A35); Fury red is reserved
// for "outdated", so no section uses it.
export const NAV: DocGroup[] = [
  { group: "Getting started", hue: "var(--d-calm)", pages: [
    { slug: "introduction", title: "Introduction", lede: "A rules assistant for Riftbound that answers as of a date, with versioned citations." },
    { slug: "installation", title: "Installation", lede: "Set up the database, the models and the rules on your computer." },
    { slug: "quick-start", title: "Quick start", lede: "Your first date-aware search, from the terminal." },
  ] },
  { group: "Connect", hue: "var(--d-body)", pages: [
    { slug: "claude-desktop", title: "Claude Desktop", lede: "Give Claude the rules tools through MCP. Runs locally; nothing leaves your machine." },
    { slug: "local-app", title: "Local web app", lede: "Ask questions in your browser, against the copy on your own machine.", soon: true },
  ] },
  { group: "Tools reference", hue: "var(--d-mind)", pages: [
    { slug: "search-rules", title: "search_rules", lede: "Find the rules that answer a question, using only rules in force on a date." },
    { slug: "ask", title: "ask", lede: "The full agent: an answer with versioned citations and a confidence score.", soon: true },
    { slug: "what-changed", title: "what_changed", lede: "How a rule changed between two versions, word by word." },
    { slug: "get-rule", title: "get_rule", lede: "The exact text of one rule in one version." },
    { slug: "list-versions", title: "list_versions", lede: "Every rules version and the dates it was in force." },
  ] },
  { group: "How it works", hue: "var(--d-chaos)", pages: [
    { slug: "versions-and-dates", title: "Versions and dates", lede: "The printed date on a rules document is not the day it took effect." },
    { slug: "why-naive-search-fails", title: "Why naive search fails", lede: "Several versions of nearly the same rule crowd the results." },
    { slug: "search-pipeline", title: "Search pipeline", lede: "What runs between your question and the passages." },
  ] },
  { group: "Evaluation", hue: "var(--d-order)", pages: [
    { slug: "question-set", title: "The question set", lede: "224 labelled questions, three groups, reported separately." },
  ] },
  { group: "Reference", hue: "var(--m-silver)", pages: [
    { slug: "changelog", title: "Changelog", lede: "What changed in the tool, newest first." },
    { slug: "credits", title: "Credits and licences", lede: "Who made the content this project builds on." },
  ] },
];

export const PAGES = NAV.flatMap((g) => g.pages.map((p) => ({ ...p, group: g.group, hue: g.hue })));

export function findPage(slug: string) {
  const i = PAGES.findIndex((p) => p.slug === slug);
  return i < 0 ? null : { page: PAGES[i], prev: PAGES[i - 1] ?? null, next: PAGES[i + 1] ?? null };
}

export const slugify = (s: string) =>
  s.toLowerCase().replace(/[`*_]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
