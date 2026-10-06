// Landing stat tiles. Every number says what it measures and which search
// produced it (the user's review), and every number comes from the export.
import { best, dateFilter, interval, naive, pct, type Rate } from "@/lib/results";

function Tile({ title, unit, was, now, wasWho, nowWho, note }: {
  title: string; unit: string; was: Rate; now: Rate; wasWho: string; nowWho: string; note: string;
}) {
  return (
    <div>
      <span className="k">{title}</span>
      <div className="pair">
        <div className="was"><span className="num">{pct(was.p)}</span><span className="unit">{unit}</span><span className="who">{wasWho}</span></div>
        <span className="arrow" aria-hidden="true">→</span>
        <div className="now"><span className="num">{pct(now.p)}</span><span className="unit">{unit}</span><span className="who">{nowWho}</span></div>
      </div>
      <span className="n">{note}</span>
    </div>
  );
}

export function StatTiles() {
  const vc = "version-change", er = "expert-ruling";
  const of0 = naive.groups[vc].outdated_above_hit5, of1 = dateFilter.groups[vc].outdated_above_hit5;
  const v0 = naive.groups[vc].at5, v1 = best.groups[vc].at5;
  const e0 = naive.groups[er].at5, e1 = best.groups[er].at5;
  return (
    <section className="proof" aria-label="Measured results">
      <Tile title="Outdated rule shown first" unit="failure rate" was={of0} now={of1} wasWho="naive search" nowWho="date filter"
        note={`On ${of0.n} version-change questions, naive search ranked an outdated rule above the current one ${of0.k} times. With the date filter: ${of1.k} times.`} />
      <Tile title="Right rule found, version changes" unit="hit rate" was={v0} now={v1} wasWho="naive search" nowWho="current search"
        note={`Right rule, right version, in the top 5 results: ${v0.k} of ${v0.n} questions before, ${v1.k} of ${v1.n} now (date filter plus the Qwen3 embedder). 95% interval for ${pct(v1.p)}: ${interval(v1)}.`} />
      <Tile title="Right rule found, expert rulings" unit="hit rate" was={e0} now={e1} wasWho="naive search" nowWho="current search"
        note={`${e1.n} rulings by an experienced rules author: ${e0.k} found before, ${e1.k} now. 95% interval for ${pct(e1.p)}: ${interval(e1)}.`} />
    </section>
  );
}
