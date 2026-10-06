"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "@/lib/docs";

export function DocsSidebar() {
  const path = usePathname() || "";
  const current = path === "/docs/" || path === "/docs" ? "introduction" : path.split("/")[2];
  return (
    <aside className="sidebar" aria-label="Documentation">
      {NAV.map((g) => (
        <div key={g.group}>
          <h4 style={{ "--sec": g.hue } as React.CSSProperties}>{g.group}</h4>
          {g.pages.map((p) => (
            <Link key={p.slug} href={`/docs/${p.slug}/`} aria-current={p.slug === current ? "page" : undefined}>
              {g.group === "Tools reference" ? <code>{p.title}</code> : p.title}
              {p.soon && <span className="soon">soon</span>}
            </Link>
          ))}
        </div>
      ))}
      <h4 style={{ "--sec": "var(--d-order)" } as React.CSSProperties}>Measured</h4>
      <Link href="/results/">Results</Link>
    </aside>
  );
}
