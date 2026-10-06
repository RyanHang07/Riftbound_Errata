"use client";
// Top nav. One diamond slides between the active section links (A39 build
// notes): hidden on the landing page, dropping in the first time a section
// is active, by click or by loading straight into it.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { REPO } from "@/lib/github";

const LINKS = [
  { href: "/docs/", label: "Docs", match: (p: string) => p.startsWith("/docs") && !p.startsWith("/docs/changelog") },
  { href: "/docs/changelog/", label: "Changelog", match: (p: string) => p.startsWith("/docs/changelog") },
  { href: "/results/", label: "Results", match: (p: string) => p.startsWith("/results"), opt: true },
];

export function Nav({ stars }: { stars: number | null }) {
  const path = usePathname() || "/";
  const refs = useRef<(HTMLAnchorElement | null)[]>([]);
  const [dia, setDia] = useState<{ x: number; on: boolean; jump: boolean }>({ x: 0, on: false, jump: true });
  const active = LINKS.findIndex((l) => l.match(path));

  useLayoutEffect(() => {
    const place = () => {
      const a = refs.current[active];
      if (active < 0 || !a || !a.offsetParent) return setDia((d) => ({ ...d, on: false }));
      const x = a.offsetLeft + a.offsetWidth / 2;
      setDia((d) => (d.on ? { x, on: true, jump: false } : { x, on: false, jump: true }));
    };
    place();
    addEventListener("resize", place);
    document.fonts?.ready.then(place);
    return () => removeEventListener("resize", place);
  }, [active]);
  // Second step of the entrance: positioned without a transition, then shown.
  useEffect(() => {
    if (active >= 0 && !dia.on && dia.jump) requestAnimationFrame(() => setDia((d) => ({ ...d, on: true, jump: false })));
  }, [active, dia.on, dia.jump]);

  return (
    <header className="nav">
      <div className="nav-inner">
        <Link className="brand" href="/">
          <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="14" height="17" rx="2" fill="none" stroke="currentColor" strokeWidth="1.8" /><rect x="7" y="2" width="14" height="17" rx="2" fill="var(--bg)" stroke="currentColor" strokeWidth="1.8" /><path d="M10 8h8M10 11.5h8M10 15h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
          <span className="brand-name">rb_errata</span>
        </Link>
        <nav className="nav-links" aria-label="Main">
          {LINKS.map((l, i) => (
            <Link key={l.href} href={l.href} ref={(el) => { refs.current[i] = el; }} className={l.opt ? "opt" : undefined} aria-current={i === active ? "page" : undefined}>
              {l.label}
            </Link>
          ))}
          <span className={`nav-dia${dia.on ? " on" : ""}${dia.jump ? " jump" : ""}`} style={{ "--x": `${dia.x}px` } as React.CSSProperties} aria-hidden="true" />
        </nav>
        <div className="nav-right">
          <button className="search-btn" type="button" aria-label="Search documentation" onClick={() => dispatchEvent(new Event("open-command-menu"))}>
            <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" /><path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
            <span className="label">Search documentation...</span><kbd>⌘K</kbd>
          </button>
          <a className="icon-btn gh" href={`https://github.com/${REPO}`} aria-label="GitHub repository">
            <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.33-1.28-1.69-1.28-1.69-1.05-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.68 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.83 1.19 3.09 0 4.41-2.69 5.39-5.25 5.67.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z" /></svg>
            {stars !== null && <span className="stars">★ {stars}</span>}
          </a>
        </div>
      </div>
    </header>
  );
}
