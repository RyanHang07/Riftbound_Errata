// The local app (slice 17, SURFACE.md section 2): Ask, Search, What changed,
// Versions, and a drawer that opens any cited rule. Everything is fetched from
// the local API; rule text is shown here and never leaves the machine.
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { api, fmt, REF, today, type AskResult, type Changed, type Passage, type Rule, type SearchResult, type VersionRow } from "./api";

const TABS = ["Ask", "Search", "What changed", "Versions"] as const;
type Tab = (typeof TABS)[number];

export default function App() {
  const [tab, setTab] = useState<Tab>("Ask");
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="mx-auto max-w-4xl px-4 pb-24">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line py-4">
        <div className="font-display text-xl text-accent">rb_errata <span className="font-sans text-sm text-muted">· local</span></div>
        <nav className="flex gap-1">
          {TABS.map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`rounded px-3 py-1.5 text-[15px] font-medium ${tab === t ? "bg-accent-soft text-head" : "text-muted hover:text-head"}`}>
              {t}
            </button>
          ))}
        </nav>
      </header>
      <main className="pt-6">
        {/* Every screen stays mounted, so switching tabs keeps each one's results. */}
        <div hidden={tab !== "Ask"}><AskView onOpen={setOpen} /></div>
        <div hidden={tab !== "Search"}><SearchView onOpen={setOpen} /></div>
        <div hidden={tab !== "What changed"}><ChangedView /></div>
        <div hidden={tab !== "Versions"}><VersionsView /></div>
      </main>
      {/* Required verbatim by Riot's Legal Jibber Jabber (section 6) and the Riftbound Developer API Policy. */}
      <footer className="mt-16 border-t border-line pt-4 text-xs text-muted">
        rb_errata was created under Riot Games&apos; &ldquo;Legal Jibber Jabber&rdquo; policy using assets owned by Riot Games. Riot Games does not endorse or sponsor this project. rb_errata isn&apos;t endorsed by Riot Games and doesn&apos;t reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
      </footer>
      {open && <RuleDrawer refId={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

// --- shared pieces ------------------------------------------------------------

function useCall<T>() {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const run = async (p: Promise<T>) => {
    setBusy(true); setError(null);
    try { setData(await p); } catch (e) { setError((e as Error).message); setData(null); } finally { setBusy(false); }
  };
  return { data, error, busy, run };
}

const Panel = ({ children, className = "" }: { children: ReactNode; className?: string }) =>
  <div className={`rounded border border-line bg-surface p-4 ${className}`}>{children}</div>;

const ErrorBox = ({ text }: { text: string | null }) =>
  text ? <Panel className="mt-4 border-red-900 text-red-300">{text}</Panel> : null;

const Warnings = ({ items }: { items: string[] }) =>
  items.length ? <div className="mt-4 space-y-2">{items.map((w) => <Panel key={w} className="border-warn/60 text-warn">{w}</Panel>)}</div> : null;

function QueryForm({ onSubmit, busy, label, extra }: { onSubmit: (q: string, d: string) => void; busy: boolean; label: string; extra?: ReactNode }) {
  const [q, setQ] = useState("");
  const [d, setD] = useState(today());
  const submit = (e: FormEvent) => { e.preventDefault(); if (q.trim()) onSubmit(q, d); };
  return (
    <form onSubmit={submit} className="space-y-3">
      <textarea value={q} onChange={(e) => setQ(e.target.value)} rows={3} placeholder="Does a countered spell still count for Legion?"
        className="w-full rounded border border-line bg-surface p-3 outline-none focus:border-accent" />
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm text-muted">As of <input type="date" value={d} onChange={(e) => setD(e.target.value)}
          className="ml-2 rounded border border-line bg-surface px-2 py-1 text-head" /></label>
        {extra}
        <button disabled={busy} className="ml-auto rounded bg-accent px-4 py-1.5 text-on-accent hover:bg-accent-hover disabled:opacity-50">
          {busy ? "Working…" : label}
        </button>
      </div>
    </form>
  );
}

/** Answer text with every version-qualified reference turned into a button. */
function Cited({ text, onOpen }: { text: string; onOpen: (r: string) => void }) {
  const parts: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(REF)) {
    parts.push(text.slice(last, m.index));
    parts.push(<button key={m.index} onClick={() => onOpen(m[0])} className="rounded bg-surface-2 px-1 font-mono text-sm text-accent hover:text-head hover:underline">{m[0]}</button>);
    last = (m.index ?? 0) + m[0].length;
  }
  parts.push(text.slice(last));
  return <p className="whitespace-pre-wrap leading-relaxed">{parts}</p>;
}

const WindowLine = ({ w }: { w: { version: string; valid_from: string; valid_to: string | null; newer_version_exists: boolean } }) => (
  <span className="text-sm text-muted">
    v{w.version} · in force {fmt(w.valid_from)} to {fmt(w.valid_to)}
    {w.newer_version_exists && <span className="ml-2 rounded border border-warn/60 px-1.5 text-xs text-warn">newer version exists</span>}
  </span>
);

// --- screens ---------------------------------------------------------------------

function AskView({ onOpen }: { onOpen: (r: string) => void }) {
  const { data, error, busy, run } = useCall<AskResult>();
  return (
    <section>
      <QueryForm busy={busy} label="Ask" onSubmit={(q, d) => run(api.ask(q, d))} />
      <ErrorBox text={error} />
      {data && (
        <>
          <Warnings items={data.warnings} />
          <Panel className="mt-4">
            <Cited text={data.answer} onOpen={onOpen} />
            <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-3 text-sm">
              <Confidence value={data.confidence} standing={data.confidence_standing} />
              {data.re_searched && <span className="text-muted">searched twice (low first confidence)</span>}
            </div>
          </Panel>
          <h3 className="mt-6 font-display text-accent">Sources</h3>
          <ul className="mt-2 space-y-2">
            {data.sources.map((s) => (
              <li key={s.ref}><Panel className="flex flex-wrap items-center justify-between gap-2 py-2">
                <button onClick={() => onOpen(s.ref)} className="font-mono text-accent hover:text-head hover:underline">{s.ref}</button>
                <WindowLine w={s} />
              </Panel></li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function Confidence({ value, standing }: { value: number | null; standing: string }) {
  if (value === null) return <span className="text-muted">No confidence score: {standing}</span>;
  const uncalibrated = standing.startsWith("UNCALIBRATED");
  return (
    <span title={standing} className={`rounded px-2 py-0.5 ${uncalibrated ? "border border-warn/60 text-warn" : "bg-accent-soft text-head"}`}>
      confidence {Math.round(value * 100)}%{uncalibrated ? " · uncalibrated, not a probability" : ""}
    </span>
  );
}

function SearchView({ onOpen }: { onOpen: (r: string) => void }) {
  const { data, error, busy, run } = useCall<SearchResult>();
  const [k, setK] = useState(5);
  const kField = <label className="text-sm text-muted">Results <input type="number" min={1} max={20} value={k}
    onChange={(e) => setK(Number(e.target.value))} className="ml-2 w-16 rounded border border-line bg-surface px-2 py-1 text-head" /></label>;
  return (
    <section>
      <QueryForm busy={busy} label="Search" extra={kField} onSubmit={(q, d) => run(api.search(q, d, k))} />
      <ErrorBox text={error} />
      {data && (
        <>
          <p className="mt-4 text-sm text-muted">Only rules in force on {fmt(data.as_of)} (v{data.version_in_effect}).</p>
          <Warnings items={data.warnings} />
          <ol className="mt-3 space-y-3">{data.passages.map((p) => <PassageCard key={p.ref} p={p} onOpen={onOpen} />)}</ol>
        </>
      )}
    </section>
  );
}

function PassageCard({ p, onOpen }: { p: Passage; onOpen: (r: string) => void }) {
  return (
    <li><Panel>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <button onClick={() => onOpen(p.ref)} className="font-mono text-accent hover:text-head hover:underline">{p.ref}</button>
        <WindowLine w={p} />
      </div>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">{p.text}</p>
    </Panel></li>
  );
}

function useVersions() {
  const [rows, setRows] = useState<VersionRow[]>([]);
  useEffect(() => { api.versions().then((v) => setRows(v.versions)).catch(() => setRows([])); }, []);
  return rows;
}

function ChangedView() {
  const versions = useVersions().filter((v) => v.searchable).map((v) => v.version);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [ref, setRef] = useState("");
  const { data, error, busy, run } = useCall<Changed>();
  useEffect(() => {
    if (versions.length > 1 && !from) { setFrom(versions[versions.length - 2]); setTo(versions[versions.length - 1]); }
  }, [versions, from]);
  const pick = (value: string, set: (v: string) => void) => (
    <select value={value} onChange={(e) => set(e.target.value)} className="rounded border border-line bg-surface px-2 py-1">
      {versions.map((v) => <option key={v}>{v}</option>)}
    </select>
  );
  return (
    <section>
      <form className="flex flex-wrap items-center gap-3" onSubmit={(e) => { e.preventDefault(); run(api.changed(from, to, ref.trim() || undefined)); }}>
        <span className="text-sm text-muted">From</span>{pick(from, setFrom)}
        <span className="text-sm text-muted">to</span>{pick(to, setTo)}
        <input value={ref} onChange={(e) => setRef(e.target.value)} placeholder="optional: core@1.4:419.4.b"
          className="min-w-56 flex-1 rounded border border-line bg-surface px-2 py-1 font-mono text-sm" />
        <button disabled={busy} className="rounded bg-accent px-4 py-1.5 text-on-accent hover:bg-accent-hover disabled:opacity-50">{busy ? "Working…" : "Compare"}</button>
      </form>
      <p className="mt-2 text-sm text-muted">Rules are matched by wording, never by number: Riot renumbers hundreds at every update.</p>
      <ErrorBox text={error} />
      {data && "status" in data && (
        <Panel className="mt-4"><p className="font-display text-accent">{data.status}</p><Diff old={data.old} next={data.new} /></Panel>
      )}
      {data && "counts" in data && (
        <div className="mt-4 space-y-3">
          <p className="text-sm text-muted">{data.counts.changed} changed · {data.counts.added} added · {data.counts.removed} removed (meaning-flipping changes first)</p>
          {data.changed.map((c, i) => <Panel key={i}><Diff old={c.old} next={c.new} /></Panel>)}
        </div>
      )}
    </section>
  );
}

const Diff = ({ old, next }: { old: { ref: string; text: string } | null; next: { ref: string; text: string } | null }) => (
  <div className="mt-2 grid gap-3 md:grid-cols-2">
    {[["Before", old], ["After", next]].map(([label, side]) => {
      const s = side as { ref: string; text: string } | null;
      return (
        <div key={label as string}>
          <div className="text-xs font-medium text-muted">{label as string} {s && <span className="font-mono normal-case text-accent">{s.ref}</span>}</div>
          <p className="mt-1 text-sm leading-relaxed">{s ? s.text : <em className="text-muted">none</em>}</p>
        </div>
      );
    })}
  </div>
);

function VersionsView() {
  const rows = useVersions();
  return (
    <ol className="space-y-2">
      {rows.map((v) => (
        <li key={v.version}><Panel className={`flex flex-wrap items-center justify-between gap-2 ${v.searchable ? "" : "opacity-70"}`}>
          <span className="font-display text-lg text-accent">v{v.version}</span>
          {v.searchable && v.valid_from
            ? <span className="text-sm text-muted">in force {fmt(v.valid_from)} to {fmt(v.valid_to ?? null)}{v.date_basis === "announcement-date" && " · date from the announcement"}</span>
            : <span className="text-sm text-warn">not searchable: {v.reason}</span>}
        </Panel></li>
      ))}
    </ol>
  );
}

function RuleDrawer({ refId, onClose }: { refId: string; onClose: () => void }) {
  const [rule, setRule] = useState<Rule | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setRule(null); setError(null);
    api.rule(refId).then(setRule).catch((e: Error) => setError(e.message));
  }, [refId]);
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-10 flex justify-end bg-scrim" onClick={onClose}>
      <aside className="h-full w-full max-w-md overflow-y-auto border-l border-line-strong bg-surface p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <span className="font-mono text-accent">{refId}</span>
          <button onClick={onClose} className="text-muted hover:text-head" aria-label="Close">✕</button>
        </div>
        {error && <p className="mt-4 text-red-300">{error}</p>}
        {!rule && !error && <p className="mt-4 text-muted">Reading the rules PDF (the first rule from a version takes a few seconds)…</p>}
        {rule && <><div className="mt-2"><WindowLine w={rule} /></div><p className="mt-4 leading-relaxed">{rule.text}</p></>}
      </aside>
    </div>
  );
}
