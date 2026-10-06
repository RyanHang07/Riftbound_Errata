// "On this page": the h2 headings of an MDX file, read at build time. The
// same slugify gives the headings their ids (mdx-components.tsx).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { slugify } from "@/lib/docs";

export function toc(slug: string) {
  const src = readFileSync(join(process.cwd(), "content/docs", `${slug}.mdx`), "utf8");
  return [...src.matchAll(/^## (.+)$/gm)].map((m) => ({ id: slugify(m[1]), title: m[1].replace(/[`*]/g, "") }));
}
