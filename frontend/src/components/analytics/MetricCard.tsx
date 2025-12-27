import React from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  /**
   * Card title
   */
  title: string;

  /**
   * Card description/subtitle
   */
  description?: string;

  /**
   * Main metric value to display
   */
  value: number | string;

  /**
   * Format for displaying the value
   */
  format?: 'number' | 'percentage' | 'currency' | 'custom';

  /**
   * Number of decimal places to show
   */
  decimals?: number;

  /**
   * Icon to display in header
   */
  icon?: LucideIcon;

  /**
   * Icon color class
   */
  iconColor?: string;

  /**
   * Secondary values or badges
   */
  badges?: Array<{
    label: string;
    value: string | number;
    variant?: 'default' | 'secondary' | 'outline' | 'destructive';
  }>;

  /**
   * Show trend indicator
   */
  trend?: {
    value: number;
    isPositive: boolean;
    label?: string;
  };

  /**
   * Show trend percentage
   */
  showTrendPercent?: boolean;

  /**
   * Background color
   */
  bgColor?: string;

  /**
   * Hover effect
   */
  interactive?: boolean;

  /**
   * Click handler for interactive mode
   */
  onClick?: () => void;

  /**
   * Content to render in footer
   */
  footer?: React.ReactNode;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Metric Card Component
 *
 * Reusable card for displaying KPI metrics with:
 * - Formatted values (percentage, currency, etc.)
 * - Trend indicators (up/down)
 * - Icon support
 * - Badge support for additional data
 * - Interactive mode for drill-down
 *
 * @example
 * ```tsx
 * // Simple KPI
 * <MetricCard
 *   title="Total Students"
 *   value={45}
 *   icon={Users}
 * />
 *
 * // With trend
 * <MetricCard
 *   title="Completion Rate"
 *   value={82}
 *   format="percentage"
 *   trend={{ value: 5, isPositive: true }}
 *   icon={Target}
 * />
 *
 * // With badges
 * <MetricCard
 *   title="Average Score"
 *   value={72.3}
 *   format="percentage"
 *   badges={[
 *     { label: 'Max', value: 98 },
 *     { label: 'Min', value: 45 }
 *   ]}
 *   icon={Award}
 * />
 *
 * // Interactive card
 * <MetricCard
 *   title="Classes"
 *   value={8}
 *   interactive
 *   onClick={() => navigate('/analytics/classes')}
 *   icon={BookOpen}
 * />
 * ```
 */
export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  description,
  value,
  format = 'number',
  decimals = 1,
  icon: Icon,
  iconColor = 'text-muted-foreground',
  badges = [],
  trend,
  showTrendPercent = true,
  bgColor,
  interactive = false,
  onClick,
  footer,
  className = '',
}) => {
  /**
   * Format the metric value
   */
  const formatValue = (val: number | string): string => {
    if (typeof val === 'string') return val;

    switch (format) {
      case 'percentage':
        return `${(Math.round(val * Math.pow(10, decimals)) / Math.pow(10, decimals)).toFixed(decimals)}%`;
      case 'currency':
        return `$${(Math.round(val * Math.pow(10, decimals)) / Math.pow(10, decimals)).toFixed(decimals)}`;
      case 'number':
        return Math.round(val * Math.pow(10, decimals)) / Math.pow(10, decimals) === Math.round(val)
          ? Math.round(val).toString()
          : (Math.round(val * Math.pow(10, decimals)) / Math.pow(10, decimals)).toFixed(decimals);
      case 'custom':
      default:
        return val.toString();
    }
  };

  const formattedValue = formatValue(value);

  return (
    <Card
      className={`${interactive ? 'cursor-pointer hover:shadow-lg transition-all' : ''} ${className}`}
      onClick={interactive ? onClick : undefined}
      style={bgColor ? { backgroundColor: bgColor } : undefined}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          {description && (
            <CardDescription className="text-xs">{description}</CardDescription>
          )}
        </div>
        {Icon && <Icon className={`h-4 w-4 ${iconColor}`} />}
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="text-2xl font-bold">{formattedValue}</div>

        {/* Trend Indicator */}
        {trend && (
          <div className="flex items-center gap-1">
            {trend.isPositive ? (
              <TrendingUp className="h-4 w-4 text-green-600" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-600" />
            )}
            <span
              className={`text-sm font-medium ${
                trend.isPositive ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {trend.isPositive ? '+' : '-'}
              {showTrendPercent ? `${trend.value}%` : trend.value}
            </span>
            {trend.label && (
              <span className="text-xs text-muted-foreground">{trend.label}</span>
            )}
          </div>
        )}

        {/* Badges */}
        {badges.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {badges.map((badge, index) => (
              <Badge key={index} variant={badge.variant || 'outline'}>
                <span className="text-xs">
                  {badge.label}: {badge.value}
                </span>
              </Badge>
            ))}
          </div>
        )}

        {/* Footer */}
        {footer && <div className="text-xs text-muted-foreground pt-2">{footer}</div>}
      </CardContent>
    </Card>
  );
};

export default MetricCard;
