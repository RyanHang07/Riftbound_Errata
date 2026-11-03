// Typed calls to the local API (rb_errata/app.py). Shapes mirror the MCP
// tools' outputs, because both call the same Python functions.
export type Window = { version: string; valid_from: string; valid_to: string | null; newer_version_exists: boolean };
export type Passage = Window & { ref: string; rules: string[]; text: string };
export type SearchResult = { as_of: string; version_in_effect: string; method: string; warnings: string[]; passages: Passage[] };
export type AskResult = {
  as_of: string; answer: string; citations: string[]; confidence: number | null;
  confidence_standing: string; re_searched: boolean; warnings: string[]; sources: (Window & { ref: string })[];
};
export type Rule = Window & { ref: string; text: string };
export type VersionRow = Partial<Window> & { version: string; searchable: boolean; reason?: string; date_basis?: string | null; effective?: string | null };
export type Side = { ref: string; text: string } | null;
export type Changed =
  | { status: string; old: Side; new: Side }
  | { from_version: string; to_version: string; counts: Record<string, number>; changed: { old: Side; new: Side }[]; added: string[]; removed: string[] };

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init);
  const body = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
  if (!r.ok) throw new Error(body.error ?? `HTTP ${r.status}`);
  return body as T;
}
const post = <T,>(path: string, body: unknown) =>
  call<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  versions: () => call<{ versions: VersionRow[] }>("/api/versions"),
  rule: (ref: string) => call<Rule>(`/api/rule?ref=${encodeURIComponent(ref)}`),
  changed: (from: string, to: string, ref?: string) =>
    call<Changed>(`/api/changed?from=${from}&to=${to}${ref ? `&ref=${encodeURIComponent(ref)}` : ""}`),
  search: (question: string, as_of: string, k = 5) => post<SearchResult>("/api/search", { question, as_of, k }),
  ask: (question: string, as_of: string) => post<AskResult>("/api/ask", { question, as_of }),
};

export const today = () => new Date().toISOString().slice(0, 10);
export const fmt = (iso: string | null) =>
  iso ? new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }) : "now";
export const REF = /core@\d+\.\d+:\d{3}(?:\.[0-9a-z]+)*/g;
