// The thesis at a glance (A35, restyled in A58): one question, two right
// answers, by date. Shown as a rules correction: the v1.2 answer struck
// through, the v1.3 answer inserted. Paraphrase only; the refs are numbers.
// Static on purpose: both answers are visible at once, so nothing has to
// flip or animate for the point to land.
export function Redline() {
  return (
    <figure className="redline" aria-label="Example: one question, two answers by date">
      <header><span>Erratum</span><span>Core Rules v1.2 to v1.3</span></header>
      <p className="q">&ldquo;If my spell gets countered, does it still count for Legion?&rdquo;</p>
      <ol>
        <li className="was">
          <span className="sign" aria-label="Removed">&minus;</span>
          <p className="claim"><b>No.</b>Legion needed you to have played another card, and a countered card was not played.</p>
          <span className="meta"><code>core@1.2:406.4.b</code><span>12 Dec 2025 to 30 Mar 2026</span></span>
        </li>
        <li className="now">
          <span className="sign" aria-label="Inserted">+</span>
          <p className="claim"><b>Yes.</b>Play triggers still don&apos;t fire, but Legion checks whether another card was <mark>Finalized</mark>. A countered spell was.</p>
          <span className="meta"><code>core@1.3:812.1.c</code><span>since 30 Mar 2026, unchanged through v1.5</span></span>
        </li>
      </ol>
      <figcaption>Same question, two right answers. Which one you get depends on the date you ask about.</figcaption>
    </figure>
  );
}
