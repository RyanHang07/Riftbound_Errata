// Explicit imports, one per page: the bundler sees every MDX file, and a
// page listed in lib/docs.ts without content fails the build (docs-page).
import type { ComponentType } from "react";

export const CONTENT: Record<string, () => Promise<{ default: ComponentType }>> = {
  "introduction": () => import("@/content/docs/introduction.mdx"),
  "installation": () => import("@/content/docs/installation.mdx"),
  "quick-start": () => import("@/content/docs/quick-start.mdx"),
  "claude-desktop": () => import("@/content/docs/claude-desktop.mdx"),
  "local-app": () => import("@/content/docs/local-app.mdx"),
  "search-rules": () => import("@/content/docs/search-rules.mdx"),
  "ask": () => import("@/content/docs/ask.mdx"),
  "what-changed": () => import("@/content/docs/what-changed.mdx"),
  "get-rule": () => import("@/content/docs/get-rule.mdx"),
  "list-versions": () => import("@/content/docs/list-versions.mdx"),
  "versions-and-dates": () => import("@/content/docs/versions-and-dates.mdx"),
  "why-naive-search-fails": () => import("@/content/docs/why-naive-search-fails.mdx"),
  "search-pipeline": () => import("@/content/docs/search-pipeline.mdx"),
  "question-set": () => import("@/content/docs/question-set.mdx"),
  "changelog": () => import("@/content/docs/changelog.mdx"),
  "credits": () => import("@/content/docs/credits.mdx"),
};
