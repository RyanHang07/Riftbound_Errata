import { Drift } from "@/components/hero/drift";
import { FlipCard } from "@/components/hero/flip-card";
import { Motes } from "@/components/hero/motes";
import { StatTiles } from "@/components/stat-tiles";
import { Button } from "@/components/ui/button";
import { REPO } from "@/lib/github";
import { fmtDate, versions } from "@/lib/results";

export default function Home() {
  const known = versions.filter((v) => v.effective);
  const current = known[known.length - 1];
  const today = new Date().toISOString().slice(0, 10); // build date: the site is rebuilt on each deploy
  return (
    <main>
      <section className="hero-band" aria-label="Introduction">
        <Motes />
        <Drift />
        <div className="hero-inner">
          <div className="hero">
            <p className="dateline"><span className="dia" aria-hidden="true" /><span>Core Rules <b>v{current.version}</b></span><span>In force since {fmtDate(current.effective!)}</span></p>
            <h1>Rules change.<br /><em>Search engines don&apos;t notice.</em></h1>
            <p>Ask a Riftbound rules question with a date. rb_errata answers from the rules that were in force that day, and cites the exact rule and version, like <code className="inline">core@1.4:419.4.a</code>. It runs on your own computer, offline.</p>
            <div className="actions">
              <Button href="/docs/" variant="magic">Get started</Button>
              <Button href={`https://github.com/${REPO}`} variant="gold">GitHub</Button>
            </div>
          </div>
          <FlipCard />
        </div>
        <div className="timeline" aria-label="Core Rules versions">
          <ol>
            {known.map((v) => (
              <li key={v.version} className={v === current ? "now" : undefined}><b>v{v.version}</b>{fmtDate(v.effective!)}</li>
            ))}
            <li className="today">today: {fmtDate(today)}</li>
          </ol>
        </div>
      </section>

      <div className="landing">
        <StatTiles />
        <section className="features">
          <div className="feature"><span className="label">Dates</span><h3>Answers as of a date</h3>
            <p>Every rules version carries the dates it was in force. Rules that weren&apos;t in force on your date are removed before ranking, so an outdated rule can&apos;t come out on top.</p></div>
          <div className="feature"><span className="label">Tools</span><h3>Works inside Claude Desktop</h3>
            <p>An MCP server gives AI apps tools to search the rules, see what changed, read one rule and list versions. Every result says which version it came from.</p></div>
          <div className="feature"><span className="label">Local</span><h3>Local, offline, measured</h3>
            <p>Postgres and Ollama on your machine, no API key. Every claim about quality is measured on labelled questions, with the predictions that were wrong published next to the right ones.</p></div>
        </section>
        <section className="how">
          <div>
            <h2>How it works</h2>
            <ol>
              <li><b>You ask with a date.</b> &ldquo;Does a countered spell count as played?&rdquo; as of 27 May 2026.</li>
              <li><b>Only rules in force that day are searched.</b> That date falls in v1.3, so v1.4&apos;s wording is out.</li>
              <li><b>The answer cites the version.</b> Every claim points at a rule like <code className="inline">core@1.3:419.4.b</code>.</li>
            </ol>
          </div>
          <pre aria-label="Example tool call">{`// search_rules, called by Claude Desktop
{
  "question": "Does a countered spell count as played?",
  "as_of": "2026-05-27"
}
// result (rule text omitted here)
[{
  "ref": "core@1.3:419.4.b",
  "valid_from": "2026-03-30",
  "valid_to": "2026-07-24",
  "newer_version_exists": true
}]`}</pre>
        </section>
      </div>
    </main>
  );
}
