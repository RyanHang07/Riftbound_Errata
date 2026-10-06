import Link from "next/link";
import { notFound } from "next/navigation";
import { CONTENT } from "@/lib/content";
import { findPage } from "@/lib/docs";
import { toc } from "@/lib/toc";

export async function DocsPage({ slug }: { slug: string }) {
  const found = findPage(slug);
  if (!found || !CONTENT[slug]) notFound();
  const { page, prev, next } = found;
  const Body = (await CONTENT[slug]()).default;
  const headings = toc(slug);
  return (
    <>
      <article className="doc" style={{ "--sec": page.hue } as React.CSSProperties}>
        <div className="crumbs">Docs / <b>{page.group}</b></div>
        <h1>{page.title}</h1>
        <p className="lede">{page.lede}</p>
        <Body />
        <div className="pager">
          {prev ? <Link href={`/docs/${prev.slug}/`}><span>Previous</span>{prev.title}</Link> : <span />}
          {next ? <Link href={`/docs/${next.slug}/`}><span>Next</span>{next.title}</Link> : <span />}
        </div>
      </article>
      <nav className="toc" aria-label="On this page">
        <h4>On this page</h4>
        {headings.map((h) => <a key={h.id} href={`#${h.id}`}>{h.title}</a>)}
      </nav>
    </>
  );
}
