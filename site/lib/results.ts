// Typed access to site/data/results.json, written by `make site-data` from
// the committed runs (brief: split write from read). Nothing here computes a
// statistic; it only formats what the export already holds.
import data from "@/data/results.json";

export type Rate = { k: number; n: number; p: number | null; lo: number; hi: number };
export type Group = {
  at1: Rate; at3: Rate; at5: Rate; at10: Rate; at20: Rate;
  outdated_above_hit5: Rate;
  vs_paired?: { gained: number; lost: number; p: number };
};
export type Run = {
  run: string; label: string; decision: "baseline" | "kept" | "best" | "reference" | "dropped";
  paired: string | null; amendment: string; method: string; embed_model: string;
  groups: Record<string, Group>; latency_s: { median: number; p90: number } | null;
};
export type Prediction = { slice: string; prediction: string; result: string; verdict: "right" | "wrong" | "close" };
export type Card = { id: string; question: string; as_of: string; ref: string };

export const runs = data.runs as unknown as Run[];
export const predictions = data.predictions as Prediction[];
export const cards = data.cards as Card[];
export const versions = data.versions as { version: string; effective: string | null; basis: string | null }[];
export const counts = data.question_counts as Record<string, number>;
export const review = data.review as { agree: number; disagree: number; unsure: number; n: number; lo: number; hi: number };

export const naive = runs.find((r) => r.decision === "baseline")!;
export const dateFilter = runs.find((r) => r.decision === "kept")!;
export const best = runs.find((r) => r.decision === "best")!;

export const pct = (p: number | null) => (p === null ? "n/a" : `${Math.round(p * 100)}%`);
export const interval = (r: Rate) => `${Math.round(r.lo * 100)} to ${Math.round(r.hi * 100)}%`;
export const pValue = (p: number) => (p < 0.001 ? "p < 0.001" : `p = ${p < 0.01 ? p.toFixed(4) : p.toFixed(2)}`);

export function fmtDate(iso: string) {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}
