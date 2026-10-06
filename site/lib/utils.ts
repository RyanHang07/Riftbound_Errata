import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// shadcn's helper: merge class lists, later Tailwind classes win.
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
