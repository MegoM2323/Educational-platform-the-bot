export interface GraphNode {
  id: string;
  title: string;
  status: 'not_started' | 'in_progress' | 'completed' | 'locked';
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
  vx?: number;
  vy?: number;
}

export interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  type: 'prerequisite' | 'suggested';
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface ProgressNodeData {
  status: 'not_started' | 'in_progress' | 'completed' | 'locked';
  percentage: number;
  completedAt?: string;
}

export interface GraphVisualizationProps {
  data: GraphData;
  progressData?: { [nodeId: string]: ProgressNodeData };
  currentLessonId?: string;
  onNodeClick?: (nodeId: string) => void;
  onNodeHover?: (nodeId: string | null) => void;
  isEditable?: boolean;
  width?: number;
  height?: number;
  className?: string;
  showLegend?: boolean;
  animationDuration?: number;
}

export interface D3Node extends GraphNode {
  x: number;
  y: number;
  fx: number | null;
  fy: number | null;
  vx?: number;
  vy?: number;
}

export interface D3Link extends GraphLink {
  source: D3Node;
  target: D3Node;
}
