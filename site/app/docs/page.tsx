// /docs/ is the Introduction, so the nav's Docs link always lands somewhere
// definite (the mockup's Docs link was dead from the Changelog).
import { DocsPage } from "@/components/docs-page";

export default function DocsIndex() {
  return <DocsPage slug="introduction" />;
}
