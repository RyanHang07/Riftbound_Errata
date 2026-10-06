// Required by @next/mdx (App Router). Headings get ids for the "On this
// page" outline; internal links use next/link; doc components are global.
import type { MDXComponents } from "mdx/types";
import Link from "next/link";
import { Callout, Count, OutdatedFirst, Param, Params, Recall, Review, VersionsTable } from "@/components/mdx-parts";
import { slugify } from "@/lib/docs";

const text = (c: React.ReactNode): string =>
  typeof c === "string" ? c : Array.isArray(c) ? c.map(text).join("") : c && typeof c === "object" && "props" in c ? text((c as { props: { children?: React.ReactNode } }).props.children) : "";

export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    h2: ({ children }) => <h2 id={slugify(text(children))}>{children}</h2>,
    a: ({ href = "", children }) => (href.startsWith("/") ? <Link href={href}>{children}</Link> : <a href={href}>{children}</a>),
    code: ({ children }) => <code className="inline">{children}</code>,
    pre: ({ children }) => {
      // Fenced blocks: MDX wraps code in <pre><code>; drop the inline styling.
      const inner = (children as { props?: { children?: React.ReactNode } })?.props?.children ?? children;
      return <pre>{inner}</pre>;
    },
    Callout, Count, OutdatedFirst, Param, Params, Recall, Review, VersionsTable,
    ...components,
  };
}
