// Components the docs MDX can use. Numbers come from the data export, so a
// page never states a figure the committed runs don't give.
import { best, counts, fmtDate, interval, naive, pct, review, versions } from "@/lib/results";

type GroupName = "expert-ruling" | "version-change" | "expert-ruling-faq" | "ruling: cards";

/** recall@5 of the current best (or naive) configuration, with its interval. */
export function Recall({ group, run = "best", withInterval = false }: { group: GroupName; run?: "best" | "naive"; withInterval?: boolean }) {
  const r = (run === "best" ? best : naive).groups[group].at5;
  return <>{pct(r.p)}{withInterval ? ` (95% interval ${interval(r)})` : ""}</>;
}

export function OutdatedFirst() {
  const r = naive.groups["version-change"].outdated_above_hit5;
  return <>{pct(r.p)} ({r.k} of {r.n})</>;
}

export function Count({ group }: { group: string }) {
  return <>{counts[group]}</>;
}

export function Review() {
  return <>{review.agree} of {review.n} agreed, {review.unsure} unsure, {review.disagree} disagreed (95% interval for agreement {Math.round(review.lo * 100)} to {Math.round(review.hi * 100)}%)</>;
}

export function VersionsTable() {
  const known = versions.filter((v) => v.effective);
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Version</th><th>In force from</th><th>Until</th><th>Date source</th></tr></thead>
        <tbody>
          {known.map((v, i) => (
            <tr key={v.version}>
              <td>{v.version}</td><td>{fmtDate(v.effective!)}</td>
              <td>{known[i + 1] ? fmtDate(known[i + 1].effective!) : "current"}</td>
              <td>{v.basis === "announcement-date" ? "announcement date" : "stated in patch notes"}</td>
            </tr>
          ))}
          {versions.filter((v) => !v.effective).map((v) => (
            <tr key={v.version}><td>{v.version}</td><td colSpan={2}>not searchable</td><td>no effective date known</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Callout({ children }: { children: React.ReactNode }) {
  return <div className="callout">{children}</div>;
}

export function Params({ children }: { children: React.ReactNode }) {
  return <div className="params">{children}</div>;
}

export function Param({ name, type, children }: { name: string; type: string; children: React.ReactNode }) {
  return <div className="param"><div><code>{name}</code><div className="t">{type}</div></div><div>{children}</div></div>;
}
