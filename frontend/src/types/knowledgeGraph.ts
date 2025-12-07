/**
 * TypeScript types for Knowledge Graph System
 */

export type ElementType = 'text_problem' | 'quick_question' | 'theory' | 'video';

export type ProgressStatus = 'not_started' | 'in_progress' | 'completed' | 'skipped';

// Базовая структура элемента
export interface Element {
  id: string;
  title: string;
  description: string;
  element_type: ElementType;
  element_type_display: string;
  content: ElementContent;
  difficulty: number; // 1-10
  estimated_time_minutes: number;
  max_score: number;
  tags: string[];
  is_public: boolean;
  created_by: {
    id: number;
    name: string;
    email: string;
    role: string;
  };
  created_at: string;
  updated_at: string;
}

// Содержимое элемента (зависит от типа)
export type ElementContent =
  | TextProblemContent
  | QuickQuestionContent
  | TheoryContent
  | VideoContent;

export interface TextProblemContent {
  problem_text: string;
  hints?: string[];
}

export interface QuickQuestionContent {
  question: string;
  choices: string[];
  correct_answer: number; // Индекс правильного ответа
  allow_multiple?: boolean; // Для будущего расширения
}

export interface TheoryContent {
  text: string;
  sections?: {
    title: string;
    content: string;
  }[];
}

export interface VideoContent {
  url: string;
  title?: string;
  description?: string;
  duration_seconds?: number;
}

// Прогресс по элементу
export interface ElementProgress {
  id: string;
  student: string;
  student_name: string;
  element: Element;
  graph_lesson: string;
  answer: ElementAnswer | null;
  score: number | null;
  max_score: number;
  score_percent: number;
  status: ProgressStatus;
  started_at: string | null;
  completed_at: string | null;
  time_spent_seconds: number;
  attempts: number;
  created_at: string;
  updated_at: string;
}

// Ответ на элемент (зависит от типа)
export type ElementAnswer =
  | TextProblemAnswer
  | QuickQuestionAnswer
  | TheoryAnswer
  | VideoAnswer;

export interface TextProblemAnswer {
  text: string;
}

export interface QuickQuestionAnswer {
  choice: number; // Индекс выбранного ответа
}

export interface TheoryAnswer {
  viewed: boolean;
}

export interface VideoAnswer {
  watched_until: number; // Секунды
}

// Props для ElementCard
export interface ElementCardProps {
  element: Element;
  progress?: ElementProgress;
  onSubmit: (answer: ElementAnswer) => Promise<void>;
  onError?: (error: Error) => void;
  isLoading?: boolean;
  readOnly?: boolean; // Для read-only режима (админ, учитель)
}

// Props для type-specific компонентов
export interface ElementTypeProps {
  element: Element;
  progress?: ElementProgress;
  onSubmit: (answer: ElementAnswer) => Promise<void>;
  isLoading?: boolean;
  readOnly?: boolean;
}

// ============================================
// Lesson Types
// ============================================

export interface Lesson {
  id: number;
  title: string;
  description: string;
  subject: number;
  subject_name?: string;
  created_by: number;
  created_at: string;
  updated_at: string;
  is_public: boolean;
  total_duration_minutes: number;
  total_max_score: number;
  elements_count?: number;
}

// ============================================
// Knowledge Graph Types
// ============================================

export interface GraphLesson {
  id: number;
  lesson: Lesson;
  position_x: number;
  position_y: number;
  is_unlocked: boolean;
  unlocked_at?: string;
  node_color: string;
  node_size: number;
  added_at: string;
}

export interface LessonDependency {
  id: number;
  from_lesson: number;
  to_lesson: number;
  dependency_type: 'prerequisite' | 'recommended' | 'related';
  strength: number; // 1-10
  created_at: string;
}

export interface KnowledgeGraph {
  id: number;
  student: number;
  student_name?: string;
  subject: number;
  subject_name?: string;
  lessons: GraphLesson[];
  dependencies: LessonDependency[];
  created_by: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  allow_skip: boolean;
}

// ============================================
// Teacher Management Types
// ============================================

export interface Student {
  id: number;
  email: string;
  full_name: string;
  role: 'student';
}

export interface TeacherStudent extends Student {
  subjects: Array<{
    id: number;
    name: string;
  }>;
}

// ============================================
// API Request/Response Types
// ============================================

export interface AddLessonToGraphRequest {
  lesson_id: number;
  position_x?: number;
  position_y?: number;
}

export interface UpdateLessonPositionRequest {
  position_x: number;
  position_y: number;
}

export interface BatchUpdateLessonsRequest {
  lessons: Array<{
    graph_lesson_id: number;
    position_x: number;
    position_y: number;
  }>;
}

export interface AddDependencyRequest {
  to_lesson_id: number;
  dependency_type?: 'prerequisite' | 'recommended' | 'related';
  strength?: number;
}

// ============================================
// UI State Types for Graph Editor
// ============================================

export interface EditState {
  modifiedPositions: Map<number, { x: number; y: number }>; // graph_lesson_id -> position
  addedLessons: Set<number>; // lesson_ids
  removedLessons: Set<number>; // graph_lesson_ids
  addedDependencies: Array<{ from: number; to: number }>; // lesson_ids
  removedDependencies: Set<number>; // dependency_ids
}

export interface ContextMenuAction {
  label: string;
  action: (lessonId: number) => void;
  icon?: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
}

export interface GraphEditorMode {
  mode: 'view' | 'edit';
  selectedNodeId?: number; // graph_lesson_id
  hoveredNodeId?: number;
  draggedNodeId?: number;
  creatingEdge?: {
    fromLessonId: number;
  };
}

// ============================================
// Visualization Types
// ============================================

export interface GraphNode {
  id: number; // graph_lesson_id
  lessonId: number;
  lesson: Lesson;
  x: number;
  y: number;
  color: string;
  size: number;
  isLocked: boolean;
}

export interface GraphEdge {
  id: number; // dependency_id
  fromLessonId: number;
  toLessonId: number;
  type: 'prerequisite' | 'recommended' | 'related';
  strength: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
