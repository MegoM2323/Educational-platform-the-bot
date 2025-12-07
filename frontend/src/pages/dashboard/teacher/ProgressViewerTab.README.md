# Teacher Progress Viewer Tab

## Описание

Компонент для просмотра прогресса студентов по графу знаний. Предоставляет учителям полный обзор выполнения заданий студентами с детальной информацией по каждому уроку и элементу.

## Функциональность

### Основные возможности

1. **Выбор студента**
   - Dropdown-список всех студентов преподавателя
   - Поиск по имени и email

2. **Обзор прогресса**
   - Общий процент завершения
   - Количество завершённых уроков
   - Набранные баллы vs максимальные
   - Время последней активности

3. **Список уроков**
   - Фильтрация по статусу (все, не начаты, в процессе, завершены, не пройдены)
   - Прогресс-бар для каждого урока
   - Цветовая индикация статуса
   - Информация о баллах и времени

4. **Детали урока**
   - Таблица элементов с развёртыванием
   - Ответы студента на каждый элемент
   - Статистика по уроку (даты начала/завершения)
   - Правильные ответы для тестов

5. **Экспорт данных**
   - Экспорт прогресса в CSV формат
   - Скачивание файла с именем `student_progress_YYYY-MM-DD.csv`

6. **Автообновление**
   - Автоматическое обновление данных каждые 30 секунд
   - Ручное обновление по кнопке
   - Индикатор последнего обновления

## Использование

### Базовое использование

```typescript
import { ProgressViewerTab } from '@/pages/dashboard/teacher/ProgressViewerTab';

function TeacherDashboard() {
  return (
    <div>
      <ProgressViewerTab subjectId={1} />
    </div>
  );
}
```

### С параметрами

```typescript
<ProgressViewerTab
  teacherId="123"
  subjectId={5}
/>
```

## API endpoints

Компонент использует следующие backend endpoints:

1. `GET /api/materials/teacher/all-students/` - список студентов
2. `GET /api/knowledge-graph/students/{student_id}/subject/{subject_id}/` - получение graph_id
3. `GET /api/knowledge-graph/{graph_id}/progress/` - обзор прогресса
4. `GET /api/knowledge-graph/{graph_id}/students/{student_id}/progress/` - детальный прогресс по урокам
5. `GET /api/knowledge-graph/{graph_id}/students/{student_id}/lesson/{lesson_id}/` - детали урока с элементами
6. `GET /api/knowledge-graph/{graph_id}/export/?format=csv` - экспорт в CSV

## Компоненты

### ProgressViewerTab (главный)

**Props:**
- `teacherId?: string` - ID преподавателя (опционально)
- `subjectId?: number` - ID предмета для фильтрации

**Зависимости:**
- `useStudentProgress` hook для управления состоянием
- ShadCN UI компоненты (Card, Table, Select, Badge, Progress)
- Lucide icons для визуализации

### LessonCard (подкомпонент)

Карточка урока в списке слева.

**Отображает:**
- Название урока
- Статус с иконкой
- Прогресс-бар
- Количество завершённых элементов
- Баллы
- Затраченное время

### LessonDetails (подкомпонент)

Панель деталей урока справа.

**Отображает:**
- Статистику урока (завершение, баллы, даты)
- Таблицу элементов с возможностью развёртывания
- Детали каждого элемента при клике

### ElementAnswerDetails (подкомпонент)

Развёрнутые детали ответа на элемент.

**Отображает для разных типов:**
- **text_problem**: полный текст ответа
- **quick_question**: выбранный вариант + правильный ответ (с подсветкой)
- **theory**: статус просмотра
- **video**: прогресс просмотра (секунды)

## Хук useStudentProgress

### Возвращаемые значения

```typescript
interface UseStudentProgressReturn {
  // Данные
  students: StudentBasic[];
  selectedStudent: StudentBasic | null;
  graphId: number | null;
  graphProgress: StudentProgressOverview | null;
  lessonProgress: LessonProgressDetail[];
  selectedLesson: LessonProgressDetail | null;
  elementDetails: ElementProgressDetail[];

  // Состояния загрузки
  isLoadingStudents: boolean;
  isLoadingProgress: boolean;
  isLoadingLessons: boolean;
  isLoadingElements: boolean;

  // Ошибки
  studentsError: Error | null;
  progressError: Error | null;
  lessonsError: Error | null;
  elementsError: Error | null;

  // Действия
  selectStudent: (student: StudentBasic) => void;
  selectLesson: (lesson: LessonProgressDetail) => void;
  refreshProgress: () => void;
  exportProgress: () => Promise<void>;

  // Последнее обновление
  lastUpdated: Date | null;
}
```

### Параметры

```typescript
interface UseStudentProgressOptions {
  graphId?: number;
  studentId?: number;
  subjectId?: number;
  autoRefresh?: boolean;       // default: false
  refreshInterval?: number;    // default: 30000ms (30 сек)
}
```

## Типы данных

### StudentBasic

```typescript
interface StudentBasic {
  id: number;
  name: string;
  email: string;
}
```

### StudentProgressOverview

```typescript
interface StudentProgressOverview {
  student_id: number;
  student_name: string;
  student_email: string;
  completion_percentage: number;
  lessons_completed: number;
  lessons_total: number;
  total_score: number;
  max_possible_score: number;
  last_activity: string | null;
}
```

### LessonProgressDetail

```typescript
interface LessonProgressDetail {
  lesson_id: number;
  lesson_title: string;
  status: 'not_started' | 'in_progress' | 'completed' | 'failed';
  completion_percent: number;
  completed_elements: number;
  total_elements: number;
  total_score: number;
  max_possible_score: number;
  started_at: string | null;
  completed_at: string | null;
  total_time_spent_seconds: number;
}
```

### ElementProgressDetail

```typescript
interface ElementProgressDetail {
  element_id: number;
  element_type: 'text_problem' | 'quick_question' | 'theory' | 'video';
  element_title: string;
  student_answer: any;
  score: number | null;
  max_score: number;
  status: 'not_started' | 'in_progress' | 'completed' | 'skipped';
  completed_at: string | null;
  attempts: number;
  correct_answer?: number;  // Для quick_question
  choices?: string[];       // Для quick_question
}
```

## Цветовая схема статусов

- **completed** (завершён): зелёный (`bg-green-500`)
- **in_progress** (в процессе): жёлтый (`bg-yellow-500`)
- **failed** (не пройден): красный (`bg-red-500`)
- **not_started** (не начат): серый (`bg-gray-400`)

## Responsive дизайн

- **Mobile (< 640px)**: вертикальный стек, карточки на всю ширину
- **Tablet (640px - 1024px)**: 1 колонка для обзора, список уроков и детали вертикально
- **Desktop (> 1024px)**: 2-колоночный layout (список уроков слева, детали справа)

## Обработка ошибок

Компонент обрабатывает следующие ошибки:
- Ошибка загрузки списка студентов → Alert с сообщением
- Ошибка загрузки прогресса → Alert под заголовком
- Ошибка загрузки уроков → Alert в карточке списка
- Ошибка экспорта → console.error (можно добавить toast)

## Производительность

### Оптимизации

1. **TanStack Query caching**
   - Список студентов кешируется на 5 минут
   - Граф кешируется на 10 минут
   - Прогресс кешируется на 1 минуту (или согласно refreshInterval)

2. **Lazy loading**
   - Детали урока загружаются только при выборе
   - Элементы раскрываются по клику

3. **Мемоизация**
   - `useMemo` для фильтрации уроков
   - `useCallback` для обработчиков событий

4. **Скроллинг**
   - Список уроков с max-height и overflow-y: auto

## Accessibility

- Keyboard navigation: Tab, Enter для выбора студента/урока
- ARIA labels для кнопок и иконок
- Semantic HTML: Table для табличных данных
- Screen reader support: статусы озвучиваются текстом

## Тестирование

### Unit тесты (рекомендуется создать)

```typescript
// hooks/__tests__/useStudentProgress.test.ts
test('loads students on mount', async () => {
  // ...
});

test('selects student and loads progress', async () => {
  // ...
});

test('filters lessons by status', () => {
  // ...
});
```

### E2E тесты (рекомендуется создать)

```typescript
// e2e/teacher/progress-viewer.spec.ts
test('teacher views student progress', async ({ page }) => {
  await page.goto('/dashboard/teacher');
  await page.click('[data-testid="progress-tab"]');
  await page.selectOption('[data-testid="student-select"]', '1');
  await expect(page.locator('[data-testid="progress-overview"]')).toBeVisible();
});
```

## Примеры использования

### Интеграция в teacher dashboard

```typescript
// pages/dashboard/teacher/TeacherDashboard.tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ProgressViewerTab } from './ProgressViewerTab';

export default function TeacherDashboard() {
  return (
    <Tabs defaultValue="overview">
      <TabsList>
        <TabsTrigger value="overview">Обзор</TabsTrigger>
        <TabsTrigger value="materials">Материалы</TabsTrigger>
        <TabsTrigger value="progress">Прогресс студентов</TabsTrigger>
      </TabsList>

      <TabsContent value="overview">
        {/* ... */}
      </TabsContent>

      <TabsContent value="progress">
        <ProgressViewerTab subjectId={currentSubject?.id} />
      </TabsContent>
    </Tabs>
  );
}
```

### С фильтрацией по предмету

```typescript
function ProgressWithSubjectFilter() {
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | undefined>();

  return (
    <div>
      <Select onValueChange={(value) => setSelectedSubjectId(Number(value))}>
        <SelectTrigger>
          <SelectValue placeholder="Выберите предмет" />
        </SelectTrigger>
        <SelectContent>
          {subjects.map(subject => (
            <SelectItem key={subject.id} value={subject.id.toString()}>
              {subject.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <ProgressViewerTab subjectId={selectedSubjectId} />
    </div>
  );
}
```

## Связанные файлы

- `/frontend/src/integrations/api/progressViewerAPI.ts` - API client
- `/frontend/src/hooks/useStudentProgress.ts` - Custom hook
- `/backend/knowledge_graph/teacher_progress_views.py` - Backend views
- `/backend/knowledge_graph/urls.py` - URL routing

## Задачи для улучшения

- [ ] Добавить WebSocket для real-time обновлений
- [ ] Добавить возможность комментирования ответов
- [ ] Добавить кнопку "Reset Progress" для учителя
- [ ] Добавить фильтрацию по датам
- [ ] Добавить сортировку уроков (по имени, прогрессу, дате)
- [ ] Добавить графическую визуализацию прогресса (charts)
- [ ] Добавить экспорт в PDF
- [ ] Добавить возможность отправки сообщения студенту

## Лицензия

Часть проекта THE_BOT Platform
