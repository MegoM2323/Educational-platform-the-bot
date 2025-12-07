/**
 * Примеры использования компонента LessonCard
 *
 * Этот файл демонстрирует различные варианты использования компонента
 */

import { LessonCard, Lesson, LessonProgress } from './LessonCard';

// Пример данных урока
const exampleLesson: Lesson = {
  id: 1,
  title: 'Введение в квадратные уравнения',
  description: 'Базовые понятия и методы решения квадратных уравнений. Научитесь решать квадратные уравнения различными способами.',
  subject: 1,
  subject_name: 'Математика',
  is_public: true,
  total_duration_minutes: 45,
  total_max_score: 300,
  elements_count: 5,
  created_by: {
    id: 10,
    full_name: 'Иванова Мария Петровна',
  },
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
};

// Пример прогресса: урок не начат
const progressNotStarted: LessonProgress = {
  id: 1,
  student: 5,
  student_name: 'Петров Иван Сергеевич',
  graph_lesson: 1,
  lesson_title: 'Введение в квадратные уравнения',
  status: 'not_started',
  completed_elements: 0,
  total_elements: 5,
  completion_percent: 0,
  total_score: 0,
  max_possible_score: 300,
  last_activity: '2025-01-15T10:00:00Z',
  total_time_spent_seconds: 0,
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
};

// Пример прогресса: урок в процессе
const progressInProgress: LessonProgress = {
  ...progressNotStarted,
  id: 2,
  status: 'in_progress',
  completed_elements: 3,
  completion_percent: 60,
  total_score: 180,
  started_at: '2025-01-15T10:00:00Z',
  total_time_spent_seconds: 1200, // 20 минут
};

// Пример прогресса: урок завершён
const progressCompleted: LessonProgress = {
  ...progressNotStarted,
  id: 3,
  status: 'completed',
  completed_elements: 5,
  completion_percent: 100,
  total_score: 285,
  started_at: '2025-01-15T10:00:00Z',
  completed_at: '2025-01-15T10:45:00Z',
  total_time_spent_seconds: 2700, // 45 минут
};

/**
 * Пример 1: Урок не начат
 */
export const LessonCardNotStarted = () => {
  return (
    <div className="max-w-md">
      <LessonCard
        lesson={exampleLesson}
        progress={progressNotStarted}
        onClick={() => console.log('Открыт урок:', exampleLesson.id)}
      />
    </div>
  );
};

/**
 * Пример 2: Урок в процессе
 */
export const LessonCardInProgress = () => {
  return (
    <div className="max-w-md">
      <LessonCard
        lesson={exampleLesson}
        progress={progressInProgress}
        onClick={() => console.log('Продолжить урок:', exampleLesson.id)}
      />
    </div>
  );
};

/**
 * Пример 3: Урок завершён
 */
export const LessonCardCompleted = () => {
  return (
    <div className="max-w-md">
      <LessonCard
        lesson={exampleLesson}
        progress={progressCompleted}
        onClick={() => console.log('Просмотр завершённого урока:', exampleLesson.id)}
      />
    </div>
  );
};

/**
 * Пример 4: Заблокированный урок
 */
export const LessonCardLocked = () => {
  return (
    <div className="max-w-md">
      <LessonCard
        lesson={exampleLesson}
        isLocked={true}
        onClick={() => console.log('Этот урок заблокирован')}
      />
    </div>
  );
};

/**
 * Пример 5: Урок без прогресса (для учителя)
 */
export const LessonCardNoProgress = () => {
  return (
    <div className="max-w-md">
      <LessonCard
        lesson={exampleLesson}
        showPreview={true}
        onNavigate={(lessonId) => console.log('Навигация к уроку:', lessonId)}
      />
    </div>
  );
};

/**
 * Пример 6: Сетка карточек уроков
 */
export const LessonCardsGrid = () => {
  const lessons: Lesson[] = [
    exampleLesson,
    { ...exampleLesson, id: 2, title: 'Решение через дискриминант', total_duration_minutes: 30, total_max_score: 200 },
    { ...exampleLesson, id: 3, title: 'Теорема Виета', total_duration_minutes: 60, total_max_score: 400 },
    { ...exampleLesson, id: 4, title: 'Практические задачи', total_duration_minutes: 90, total_max_score: 500 },
  ];

  const progresses = [
    progressCompleted,
    progressInProgress,
    progressNotStarted,
    undefined, // Урок без прогресса (заблокирован)
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
      {lessons.map((lesson, index) => (
        <LessonCard
          key={lesson.id}
          lesson={lesson}
          progress={progresses[index]}
          isLocked={index === 3}
          onClick={() => console.log('Клик на урок:', lesson.id)}
        />
      ))}
    </div>
  );
};

/**
 * Пример 7: Использование с навигацией
 */
export const LessonCardWithNavigation = () => {
  const handleNavigate = (lessonId: number) => {
    // Пример навигации с React Router
    window.location.href = `/lessons/${lessonId}`;
  };

  return (
    <div className="max-w-md">
      <LessonCard
        lesson={exampleLesson}
        progress={progressInProgress}
        onNavigate={handleNavigate}
      />
    </div>
  );
};
