/**
 * Демонстрационная страница для LessonCard компонента
 *
 * Показывает все возможные состояния и варианты использования
 */

import { LessonCard, Lesson, LessonProgress } from '@/components/knowledge-graph/LessonCard';

// Примеры данных уроков с разной сложностью
const easyLesson: Lesson = {
  id: 1,
  title: 'Основы сложения и вычитания',
  description: 'Простые арифметические операции для начинающих',
  subject: 1,
  subject_name: 'Математика',
  is_public: true,
  total_duration_minutes: 20,
  total_max_score: 100,
  elements_count: 3,
  created_by: { id: 1, full_name: 'Иванова М.П.' },
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
};

const mediumLesson: Lesson = {
  id: 2,
  title: 'Квадратные уравнения',
  description: 'Методы решения квадратных уравнений: дискриминант, теорема Виета',
  subject: 1,
  subject_name: 'Математика',
  is_public: true,
  total_duration_minutes: 45,
  total_max_score: 300,
  elements_count: 5,
  created_by: { id: 1, full_name: 'Иванова М.П.' },
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
};

const hardLesson: Lesson = {
  id: 3,
  title: 'Интегральное исчисление',
  description: 'Методы вычисления определённых и неопределённых интегралов',
  subject: 1,
  subject_name: 'Математика',
  is_public: true,
  total_duration_minutes: 90,
  total_max_score: 500,
  elements_count: 8,
  created_by: { id: 1, full_name: 'Иванова М.П.' },
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
};

// Примеры прогресса
const notStartedProgress: LessonProgress = {
  id: 1,
  student: 1,
  student_name: 'Петров И.С.',
  graph_lesson: 1,
  lesson_title: 'Основы сложения и вычитания',
  status: 'not_started',
  completed_elements: 0,
  total_elements: 3,
  completion_percent: 0,
  total_score: 0,
  max_possible_score: 100,
  last_activity: '2025-01-15T10:00:00Z',
  total_time_spent_seconds: 0,
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
};

const inProgressProgress: LessonProgress = {
  id: 2,
  student: 1,
  student_name: 'Петров И.С.',
  graph_lesson: 2,
  lesson_title: 'Квадратные уравнения',
  status: 'in_progress',
  completed_elements: 3,
  total_elements: 5,
  completion_percent: 60,
  total_score: 180,
  max_possible_score: 300,
  started_at: '2025-01-15T10:00:00Z',
  last_activity: '2025-01-15T10:25:00Z',
  total_time_spent_seconds: 1500,
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:25:00Z',
};

const completedProgress: LessonProgress = {
  id: 3,
  student: 1,
  student_name: 'Петров И.С.',
  graph_lesson: 3,
  lesson_title: 'Интегральное исчисление',
  status: 'completed',
  completed_elements: 8,
  total_elements: 8,
  completion_percent: 100,
  total_score: 475,
  max_possible_score: 500,
  started_at: '2025-01-15T10:00:00Z',
  completed_at: '2025-01-15T11:30:00Z',
  last_activity: '2025-01-15T11:30:00Z',
  total_time_spent_seconds: 5400,
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T11:30:00Z',
};

const failedProgress: LessonProgress = {
  id: 4,
  student: 1,
  student_name: 'Петров И.С.',
  graph_lesson: 4,
  lesson_title: 'Производные',
  status: 'failed',
  completed_elements: 2,
  total_elements: 6,
  completion_percent: 33,
  total_score: 85,
  max_possible_score: 400,
  started_at: '2025-01-15T10:00:00Z',
  last_activity: '2025-01-15T10:45:00Z',
  total_time_spent_seconds: 2700,
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:45:00Z',
};

export const LessonCardDemo = () => {
  const handleClick = (title: string) => {
    console.log('Clicked on lesson:', title);
  };

  return (
    <div className="container mx-auto p-8 space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-bold">LessonCard Component Demo</h1>
        <p className="text-muted-foreground">
          Демонстрация всех состояний и вариантов использования компонента карточки урока
        </p>
      </div>

      {/* Состояния по статусу */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Состояния по статусу</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">Не начат</h3>
            <LessonCard
              lesson={easyLesson}
              progress={notStartedProgress}
              onClick={() => handleClick('Not Started')}
            />
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">В процессе</h3>
            <LessonCard
              lesson={mediumLesson}
              progress={inProgressProgress}
              onClick={() => handleClick('In Progress')}
            />
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">Завершён</h3>
            <LessonCard
              lesson={hardLesson}
              progress={completedProgress}
              onClick={() => handleClick('Completed')}
            />
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">Заблокирован</h3>
            <LessonCard
              lesson={mediumLesson}
              isLocked={true}
            />
          </div>
        </div>
      </section>

      {/* Состояния по сложности */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Уровни сложности</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-green-600">Легкий (1 звезда)</h3>
            <LessonCard
              lesson={easyLesson}
              progress={notStartedProgress}
              onClick={() => handleClick('Easy')}
            />
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-medium text-yellow-600">Средний (2 звезды)</h3>
            <LessonCard
              lesson={mediumLesson}
              progress={inProgressProgress}
              onClick={() => handleClick('Medium')}
            />
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-medium text-red-600">Сложный (3 звезды)</h3>
            <LessonCard
              lesson={hardLesson}
              progress={completedProgress}
              onClick={() => handleClick('Hard')}
            />
          </div>
        </div>
      </section>

      {/* Прогресс */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Различные уровни прогресса</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">0% прогресс</h3>
            <LessonCard
              lesson={mediumLesson}
              progress={notStartedProgress}
              onClick={() => handleClick('0%')}
            />
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">60% прогресс</h3>
            <LessonCard
              lesson={mediumLesson}
              progress={inProgressProgress}
              onClick={() => handleClick('60%')}
            />
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">100% прогресс</h3>
            <LessonCard
              lesson={mediumLesson}
              progress={completedProgress}
              onClick={() => handleClick('100%')}
            />
          </div>
        </div>
      </section>

      {/* Особые случаи */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Особые случаи</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">Без прогресса (учитель)</h3>
            <LessonCard
              lesson={mediumLesson}
              showPreview={true}
              onClick={() => handleClick('No Progress')}
            />
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">Не пройден</h3>
            <LessonCard
              lesson={{...mediumLesson, id: 4, title: 'Производные'}}
              progress={failedProgress}
              onClick={() => handleClick('Failed')}
            />
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">С навигацией</h3>
            <LessonCard
              lesson={mediumLesson}
              progress={inProgressProgress}
              onNavigate={(id) => alert(`Navigate to lesson ${id}`)}
            />
          </div>
        </div>
      </section>

      {/* Различные размеры */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Адаптивность</h2>
        <p className="text-sm text-muted-foreground">
          Компонент адаптивен и корректно отображается на разных размерах экрана
        </p>

        <div className="space-y-4">
          <div className="max-w-sm space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">Mobile (max-w-sm)</h3>
            <LessonCard
              lesson={mediumLesson}
              progress={inProgressProgress}
              onClick={() => handleClick('Mobile')}
            />
          </div>

          <div className="max-w-md space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">Tablet (max-w-md)</h3>
            <LessonCard
              lesson={mediumLesson}
              progress={inProgressProgress}
              onClick={() => handleClick('Tablet')}
            />
          </div>

          <div className="max-w-2xl space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">Desktop (max-w-2xl)</h3>
            <LessonCard
              lesson={mediumLesson}
              progress={inProgressProgress}
              onClick={() => handleClick('Desktop')}
            />
          </div>
        </div>
      </section>

      {/* Grid layout */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Grid Layout (типичное использование)</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { lesson: easyLesson, progress: completedProgress },
            { lesson: mediumLesson, progress: inProgressProgress },
            { lesson: hardLesson, progress: notStartedProgress },
            { lesson: {...easyLesson, id: 4, title: 'Умножение и деление'}, progress: undefined, locked: true },
            { lesson: {...mediumLesson, id: 5, title: 'Тригонометрия'}, progress: undefined, locked: true },
            { lesson: {...hardLesson, id: 6, title: 'Дифференциальные уравнения'}, progress: undefined, locked: true },
          ].map((item, index) => (
            <LessonCard
              key={index}
              lesson={item.lesson}
              progress={item.progress}
              isLocked={item.locked}
              onClick={() => handleClick(`Grid ${index + 1}`)}
            />
          ))}
        </div>
      </section>
    </div>
  );
};

export default LessonCardDemo;
