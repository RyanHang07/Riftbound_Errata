// Two rows of question cards drifting in opposite directions behind the
// hero (A35). Content is this project's own version-change questions, from
// the data export; each row is duplicated so the loop is seamless.
import { cards, fmtDate } from "@/lib/results";
import { CardDressing, clock } from "./wisp";

const HUES = ["mind", "calm", "body", "chaos", "order", "fury"];

function Row({ items, offset, rev }: { items: typeof cards; offset: number; rev?: boolean }) {
  const once = items.map((c, i) => ({ c, i: i + offset }));
  return (
    <div className={`drift-row${rev ? " rev" : ""}`}>
      {[...once, ...once].map(({ c, i }, n) => (
        <div key={`${c.id}-${n}`} className="qcard" aria-hidden={n >= once.length || undefined}
          style={{ "--hue": `var(--d-${HUES[i % HUES.length]})`, ...clock(i + n) } as React.CSSProperties}>
          <div className="qcard-in">
            <div className="top"><span className="gem" />as of {fmtDate(c.as_of)}</div>
            <div className="q">{c.question}</div>
            <div className="ref">{c.ref}</div>
          </div>
          <CardDressing i={i} />
        </div>
      ))}
    </div>
  );
}

export function Drift() {
  // Short questions read best on a card; take the 16 shortest, interleaved
  // so each row mixes dates and versions.
  const pick = [...cards].sort((a, b) => a.question.length - b.question.length).slice(0, 16);
  return (
    <div className="drift" aria-hidden="true">
      <Row items={pick.filter((_, i) => i % 2 === 0)} offset={0} />
      <Row items={pick.filter((_, i) => i % 2 === 1)} offset={8} rev />
    </div>
  );
}
