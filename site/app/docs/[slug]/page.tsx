import type { Metadata } from "next";
import { DocsPage } from "@/components/docs-page";
import { findPage, PAGES } from "@/lib/docs";

export const dynamicParams = false;
export const generateStaticParams = () => PAGES.map((p) => ({ slug: p.slug }));

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const found = findPage((await params).slug);
  return { title: found ? `${found.page.title} · rb_errata` : "rb_errata" };
}

export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  return <DocsPage slug={(await params).slug} />;
}
