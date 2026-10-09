import * as React from "react";
import { cn } from "@/lib/utils";

export interface OutlineButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  label?: string;
  children?: React.ReactNode;
}

/**
 * Clean dark outline button matching Image 2 design.
 * Features a single subtle rounded border, solid black background,
 * and clean typography with zero outer container boxes, no download keywords, and no icons.
 */
export const OutlineButton = React.forwardRef<
  HTMLButtonElement,
  OutlineButtonProps
>(({ className, label, children, ...props }, ref) => {
  return (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center px-4 py-2 text-sm font-medium",
        "bg-black hover:bg-zinc-900 active:bg-zinc-950",
        "text-white hover:text-zinc-100",
        "border border-zinc-700/80 hover:border-zinc-500",
        "rounded-lg transition-colors cursor-pointer",
        "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-400",
        "disabled:opacity-50 disabled:pointer-events-none select-none",
        className
      )}
      {...props}
    >
      {label || children}
    </button>
  );
});

OutlineButton.displayName = "OutlineButton";

export default OutlineButton;
