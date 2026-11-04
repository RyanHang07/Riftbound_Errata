// shadcn-style Button: variants through cva, styling through the classes in
// globals.css. "magic" and "gold" are kept as variant names so call sites
// don't change; they now mean primary (ink) and secondary (outlined).
import { cva, type VariantProps } from "class-variance-authority";
import Link from "next/link";
import { cn } from "@/lib/utils";

const button = cva("btn", {
  variants: { variant: { magic: "btn-primary", gold: "btn-ghost" } },
  defaultVariants: { variant: "gold" },
});

type Props = VariantProps<typeof button> & { href: string; className?: string; children: React.ReactNode };

export function Button({ href, variant, className, children }: Props) {
  const external = href.startsWith("http");
  return external ? (
    <a href={href} className={cn(button({ variant }), className)}>{children}</a>
  ) : (
    <Link href={href} className={cn(button({ variant }), className)}>{children}</Link>
  );
}
