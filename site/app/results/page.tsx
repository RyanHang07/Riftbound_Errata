import type { Metadata } from "next";
import { counts, interval, pct, predictions, pValue, runs, type Run } from "@/lib/results";

export const metadata: Metadata = { title: "Results · rb_errata" };

const TIER: Partial<Record<Run["decision"], string>> = { baseline: "bronze", kept: "silver", best: "gold" };
const KEPT: Record<Run["decision"], [string, string]> = {
  baseline: ["wait", "baseline"], kept: ["good", "kept"], best: ["good", "current best"],
  reference: ["wait", "reference"], dropped: ["bad", "dropped"],
};
const GROUPS = ["expert-ruling", "ruling: cards", "version-change"] as const;

function vsCell(r: Run) {
  const v = r.groups["version-change"].vs_paired;
  if (!v) return <span className="ci">baseline</span>;
  const speed = r.latency_s && r.latency_s.median > 1 ? `, ${r.latency_s.median.toFixed(1)} s per question` : "";
  return <>version changes {v.gained} gained / {v.lost} lost, {pValue(v.p)}{speed}</>;
}

export default function Results() {
  return (
    <main>
      <div className="results">
        <div>
          <h1>Results</h1>
          <p className="lede">Each row is one search configuration, run on the same {counts["expert-ruling"] + counts["expert-ruling-faq"] + counts["version-change"]} questions. A hit means the right rule, in the version in force on the question&apos;s date, is in the top 5. Brackets are 95% Wilson intervals; comparisons are exact McNemar tests on the same questions. Every row had a written prediction before it ran.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Configuration</th><th>Expert rulings ({counts["expert-ruling"]})</th><th>Card rulings ({counts["ruling: cards"]})</th><th>Version changes ({counts["version-change"]})</th><th>Against the row it was tested on</th><th>Kept?</th></tr></thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.run} data-tier={TIER[r.decision]} className={r.decision === "best" ? "best" : undefined}>
                  <td>{r.label}</td>
                  {GROUPS.map((g) => { const x = r.groups[g].at5; return <td key={g}>{pct(x.p)} <span className="ci">[{interval(x)}]</span></td>; })}
                  <td>{vsCell(r)}</td>
                  <td><span className={`pill ${KEPT[r.decision][0]}`}>{KEPT[r.decision][1]}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="legend">
          <span><i style={{ "--c": "var(--m-bronze)" } as React.CSSProperties} />Baseline</span>
          <span><i style={{ "--c": "var(--m-silver)" } as React.CSSProperties} />Kept</span>
          <span><i style={{ "--c": "var(--m-gold)" } as React.CSSProperties} />Current best</span>
          <span>No edge: tested and dropped</span>
        </div>
        <h2>Predictions against results</h2>
        <p className="lede">Written before each run. {predictions.filter((p) => p.verdict === "right").length} right, {predictions.filter((p) => p.verdict === "wrong").length} wrong.</p>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Slice</th><th>Prediction</th><th>Result</th><th>Verdict</th></tr></thead>
            <tbody>
              {predictions.map((p, i) => (
                <tr key={i}><td>{p.slice}</td><td>{p.prediction}</td><td>{p.result}</td>
                  <td><span className={`pill ${p.verdict === "wrong" ? "bad" : "good"}`}>{p.verdict}</span></td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="lede">Generated at build time from <code className="inline">site/data/results.json</code>, which <code className="inline">make site-data</code> computes from the committed runs in <code className="inline">evals/runs/</code>.</p>
      </div>
    </main>
  );
}
