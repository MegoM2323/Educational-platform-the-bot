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
