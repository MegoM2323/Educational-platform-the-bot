import { cn } from "@/lib/utils";

/**
 * Props for Spinner component
 * @typedef {Object} SpinnerProps
 * @property {string} [className] - Additional CSS classes
 * @property {string} [size="md"] - Spinner size: sm, md, lg
 */
interface SpinnerProps {
  className?: string;
  size?: "sm" | "md" | "lg";
}

const sizeClasses = {
  sm: "w-4 h-4",
  md: "w-8 h-8",
  lg: "w-12 h-12",
};

/**
 * Spinner component - Loading indicator
 *
 * @component
 * @example
 * // Small spinner
 * <Spinner size="sm" />
 *
 * // Medium spinner (default)
 * <Spinner />
 *
 * // Large spinner
 * <Spinner size="lg" />
 *
 * // With custom color
 * <Spinner className="text-red-500" />
 *
 * @param {SpinnerProps} props - Component props
 * @returns {React.ReactElement} Spinner element
 */
export function Spinner({ className, size = "md" }: SpinnerProps) {
  return (
    <div className={cn("animate-spin", sizeClasses[size], className)}>
      <svg
        className="w-full h-full text-blue-500"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        ></circle>
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        ></path>
      </svg>
    </div>
  );
}
