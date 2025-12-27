import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

/**
 * Badge component - Small, inline label with variants
 *
 * @component
 * @example
 * // Default badge
 * <Badge>New</Badge>
 *
 * // Secondary badge
 * <Badge variant="secondary">Badge</Badge>
 *
 * // Destructive badge
 * <Badge variant="destructive">Error</Badge>
 *
 * // Outline badge
 * <Badge variant="outline">Info</Badge>
 */

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

/**
 * Props for the Badge component
 * @typedef {Object} BadgeProps
 * @property {string} [variant="default"] - Badge variant: default, secondary, destructive, outline
 * @property {string} [className] - Additional CSS classes
 */
export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

/**
 * Badge component with variant support
 * @param {BadgeProps} props - Component props
 * @returns {React.ReactElement} Badge element
 */
function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
