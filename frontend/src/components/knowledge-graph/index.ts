/**
 * Knowledge Graph Components
 * Экспорт всех компонентов системы графа знаний
 */

export { ElementCard, ElementCardSkeleton } from './ElementCard';
export { TextProblem } from './element-types/TextProblem';
export { QuickQuestion } from './element-types/QuickQuestion';
export { Theory } from './element-types/Theory';
export { Video } from './element-types/Video';

// Graph Visualization
export { GraphVisualization } from './GraphVisualization';
export type {
  GraphNode,
  GraphLink,
  GraphData,
  GraphVisualizationProps,
  ProgressNodeData,
} from './graph-types';
export {
  transformGraphData,
  validateGraphData,
  getNodeColor,
  CONSTANTS,
  NODE_COLORS,
} from './graph-utils';

// Progress Visualization
export {
  ProgressLegend,
  ProgressLegendCompact,
  ProgressLegendMobile,
  ProgressLegendDesktop,
} from './ProgressLegend';
export type { ProgressLegendProps } from './ProgressLegend';
export {
  GraphStatistics,
  GraphStatisticsCompact,
} from './GraphStatistics';
export type { GraphStatisticsProps } from './GraphStatistics';
export {
  getNodeColorByStatus,
  getNodeOpacity as getProgressNodeOpacity,
  formatProgressLabel,
  getNodeSize,
  animateProgressTransition,
  getCurrentLessonGlow,
  calculateOverallProgress,
  getStatusText,
  PROGRESS_COLORS,
  PROGRESS_HOVER_COLORS,
} from './progressUtils';
export type {
  ProgressData,
  ProgressStatus,
  ProgressTransition,
} from './progressUtils';
