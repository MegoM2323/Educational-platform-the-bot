/**
 * Teacher Progress Viewer Tab (T605)
 * Страница просмотра прогресса студентов по графу знаний
 */
import React, { useState, useMemo } from 'react';
import { useStudentProgress } from '@/hooks/useStudentProgress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Download,
  RefreshCw,
  User,
  BookOpen,
  Clock,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Circle,
  PlayCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { LessonProgressDetail, ElementProgressDetail } from '@/integrations/api/progressViewerAPI';

interface ProgressViewerTabProps {
  teacherId?: string;
  subjectId?: number; // ID предмета для фильтрации
}

export const ProgressViewerTab: React.FC<ProgressViewerTabProps> = ({ subjectId }) => {
  const {
    students,
    selectedStudent,
    graphProgress,
    lessonProgress,
    selectedLesson,
    elementDetails,
    isLoadingStudents,
    isLoadingProgress,
    isLoadingLessons,
    isLoadingElements,
    studentsError,
    progressError,
    lessonsError,
    selectStudent,
    selectLesson,
    refreshProgress,
    exportProgress,
    lastUpdated,
  } = useStudentProgress({ subjectId, autoRefresh: true, refreshInterval: 30000 });

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [expandedElements, setExpandedElements] = useState<Set<number>>(new Set());

  // Фильтрация уроков по статусу
  const filteredLessons = useMemo(() => {
    if (statusFilter === 'all') return lessonProgress;
    return lessonProgress.filter((lesson) => lesson.status === statusFilter);
  }, [lessonProgress, statusFilter]);

  // Получить цвет статуса
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'in_progress':
        return 'bg-yellow-500';
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-gray-400';
    }
  };

  // Получить иконку статуса
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-4 w-4" />;
      case 'in_progress':
        return <PlayCircle className="h-4 w-4" />;
      case 'failed':
        return <XCircle className="h-4 w-4" />;
      default:
        return <Circle className="h-4 w-4" />;
    }
  };

  // Получить текст статуса
  const getStatusText = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'Завершён';
      case 'in_progress':
        return 'В процессе';
      case 'failed':
        return 'Не пройден';
      default:
        return 'Не начат';
    }
  };

  // Форматирование времени
  const formatTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}ч ${minutes}м`;
    }
    return `${minutes}м`;
  };

  // Форматирование даты
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Форматирование относительного времени
  const formatRelativeTime = (dateString: string | null): string => {
    if (!dateString) return 'Никогда';
    const now = new Date();
    const date = new Date(dateString);
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMinutes < 1) return 'Только что';
    if (diffMinutes < 60) return `${diffMinutes} мин. назад`;
    if (diffHours < 24) return `${diffHours} ч. назад`;
    if (diffDays < 7) return `${diffDays} дн. назад`;
    return formatDate(dateString);
  };

  // Toggle развёртывание элемента
  const toggleElementExpansion = (elementId: number) => {
    setExpandedElements((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(elementId)) {
        newSet.delete(elementId);
      } else {
        newSet.add(elementId);
      }
      return newSet;
    });
  };

  // Обработка экспорта
  const handleExport = async () => {
    try {
      await exportProgress();
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  // Рендеринг ошибок
  if (studentsError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Ошибка загрузки списка студентов: {studentsError.message}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      {/* Заголовок и фильтры */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-bold">Прогресс студентов</h2>
          <p className="text-sm text-muted-foreground">
            Просмотр прогресса по графу знаний
          </p>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          {lastUpdated && (
            <span className="text-xs text-muted-foreground">
              Обновлено: {formatRelativeTime(lastUpdated.toISOString())}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={refreshProgress}
            disabled={isLoadingProgress}
          >
            <RefreshCw className={cn('mr-2 h-4 w-4', isLoadingProgress && 'animate-spin')} />
            Обновить
          </Button>
        </div>
      </div>

      {/* Селектор студента */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Выбор студента</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoadingStudents ? (
            <Skeleton className="h-10 w-full" />
          ) : (
            <Select
              value={selectedStudent?.id.toString()}
              onValueChange={(value) => {
                const student = students.find((s) => s.id.toString() === value);
                if (student) selectStudent(student);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Выберите студента" />
              </SelectTrigger>
              <SelectContent>
                {students.map((student) => (
                  <SelectItem key={student.id} value={student.id.toString()}>
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4" />
                      <span>{student.name}</span>
                      <span className="text-xs text-muted-foreground">({student.email})</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </CardContent>
      </Card>

      {/* Обзор прогресса */}
      {selectedStudent && (
        <>
          {isLoadingProgress ? (
            <div className="grid gap-4 md:grid-cols-4">
              {[...Array(4)].map((_, i) => (
                <Card key={`progress-skeleton-${i}`}>
                  <CardContent className="p-6">
                    <Skeleton className="h-20 w-full" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : progressError ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Ошибка загрузки прогресса: {progressError.message}
              </AlertDescription>
            </Alert>
          ) : graphProgress ? (
            <div className="grid gap-4 md:grid-cols-4">
              {/* Общее завершение */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Общее завершение
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">
                    {graphProgress.completion_percentage.toFixed(0)}%
                  </div>
                  <Progress
                    value={graphProgress.completion_percentage}
                    className="mt-2"
                  />
                </CardContent>
              </Card>

              {/* Уроки */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <BookOpen className="h-4 w-4" />
                    Уроки
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">
                    {graphProgress.lessons_completed}/{graphProgress.lessons_total}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">завершено</p>
                </CardContent>
              </Card>

              {/* Баллы */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    Баллы
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">
                    {graphProgress.total_score}/{graphProgress.max_possible_score}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {graphProgress.max_possible_score > 0
                      ? Math.round(
                          (graphProgress.total_score / graphProgress.max_possible_score) * 100
                        )
                      : 0}
                    % правильных ответов
                  </p>
                </CardContent>
              </Card>

              {/* Последняя активность */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Последняя активность
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-semibold">
                    {formatRelativeTime(graphProgress.last_activity)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {graphProgress.last_activity
                      ? formatDate(graphProgress.last_activity)
                      : 'Нет активности'}
                  </p>
                </CardContent>
              </Card>
            </div>
          ) : null}

          {/* Фильтры и экспорт */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap gap-2">
              <Button
                variant={statusFilter === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('all')}
              >
                Все
              </Button>
              <Button
                variant={statusFilter === 'not_started' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('not_started')}
              >
                Не начаты
              </Button>
              <Button
                variant={statusFilter === 'in_progress' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('in_progress')}
              >
                В процессе
              </Button>
              <Button
                variant={statusFilter === 'completed' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('completed')}
              >
                Завершены
              </Button>
              <Button
                variant={statusFilter === 'failed' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('failed')}
              >
                Не пройдены
              </Button>
            </div>

            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="mr-2 h-4 w-4" />
              Экспорт CSV
            </Button>
          </div>

          {/* Список уроков */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Левая колонка: список уроков */}
            <Card>
              <CardHeader>
                <CardTitle>Уроки ({filteredLessons.length})</CardTitle>
                <CardDescription>
                  Нажмите на урок для просмотра деталей
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isLoadingLessons ? (
                  <div className="space-y-2">
                    {[...Array(5)].map((_, i) => (
                      <Skeleton key={`lesson-skeleton-${i}`} className="h-16 w-full" />
                    ))}
                  </div>
                ) : lessonsError ? (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Ошибка загрузки уроков: {lessonsError.message}
                    </AlertDescription>
                  </Alert>
                ) : filteredLessons.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">
                    Нет уроков в выбранной категории
                  </p>
                ) : (
                  <div className="space-y-2 max-h-[600px] overflow-y-auto">
                    {filteredLessons.map((lesson) => (
                      <LessonCard
                        key={lesson.lesson_id}
                        lesson={lesson}
                        isSelected={selectedLesson?.lesson_id === lesson.lesson_id}
                        onClick={() => selectLesson(lesson)}
                        getStatusColor={getStatusColor}
                        getStatusIcon={getStatusIcon}
                        getStatusText={getStatusText}
                        formatTime={formatTime}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Правая колонка: детали урока */}
            <Card>
              <CardHeader>
                <CardTitle>Детали урока</CardTitle>
                <CardDescription>
                  {selectedLesson
                    ? `${selectedLesson.lesson_title}`
                    : 'Выберите урок для просмотра деталей'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {!selectedLesson ? (
                  <p className="text-center text-muted-foreground py-8">
                    Выберите урок из списка слева
                  </p>
                ) : isLoadingElements ? (
                  <Skeleton className="h-64 w-full" />
                ) : (
                  <LessonDetails
                    lesson={selectedLesson}
                    elements={elementDetails}
                    expandedElements={expandedElements}
                    toggleElementExpansion={toggleElementExpansion}
                    formatDate={formatDate}
                    getStatusText={getStatusText}
                    getStatusIcon={getStatusIcon}
                  />
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
};

// Компонент карточки урока
interface LessonCardProps {
  lesson: LessonProgressDetail;
  isSelected: boolean;
  onClick: () => void;
  getStatusColor: (status: string) => string;
  getStatusIcon: (status: string) => React.ReactNode;
  getStatusText: (status: string) => string;
  formatTime: (seconds: number) => string;
}

const LessonCard: React.FC<LessonCardProps> = ({
  lesson,
  isSelected,
  onClick,
  getStatusColor,
  getStatusIcon,
  getStatusText,
  formatTime,
}) => {
  return (
    <div
      className={cn(
        'p-4 border rounded-lg cursor-pointer transition-all hover:shadow-md',
        isSelected && 'border-primary bg-primary/5'
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-semibold text-sm">{lesson.lesson_title}</h4>
        <Badge
          variant="outline"
          className={cn('ml-2 flex items-center gap-1', getStatusColor(lesson.status))}
        >
          {getStatusIcon(lesson.status)}
          <span className="text-xs">{getStatusText(lesson.status)}</span>
        </Badge>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {lesson.completed_elements}/{lesson.total_elements} элементов
          </span>
          <span>{lesson.completion_percent.toFixed(0)}%</span>
        </div>
        <Progress value={lesson.completion_percent} className="h-2" />

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            Баллы: {lesson.total_score}/{lesson.max_possible_score}
          </span>
          {lesson.total_time_spent_seconds > 0 && (
            <span>Время: {formatTime(lesson.total_time_spent_seconds)}</span>
          )}
        </div>
      </div>
    </div>
  );
};

// Компонент деталей урока
interface LessonDetailsProps {
  lesson: LessonProgressDetail;
  elements: ElementProgressDetail[];
  expandedElements: Set<number>;
  toggleElementExpansion: (id: number) => void;
  formatDate: (date: string | null) => string;
  getStatusText: (status: string) => string;
  getStatusIcon: (status: string) => React.ReactNode;
}

const LessonDetails: React.FC<LessonDetailsProps> = ({
  lesson,
  elements,
  expandedElements,
  toggleElementExpansion,
  formatDate,
  getStatusText,
  getStatusIcon,
}) => {
  // Получить тип элемента на русском
  const getElementTypeText = (type: string): string => {
    switch (type) {
      case 'text_problem':
        return 'Задача';
      case 'quick_question':
        return 'Тест';
      case 'theory':
        return 'Теория';
      case 'video':
        return 'Видео';
      default:
        return type;
    }
  };

  return (
    <div className="space-y-4">
      {/* Статистика урока */}
      <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
        <div>
          <p className="text-xs text-muted-foreground">Завершение</p>
          <p className="text-lg font-semibold">{lesson.completion_percent.toFixed(0)}%</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Баллы</p>
          <p className="text-lg font-semibold">
            {lesson.total_score}/{lesson.max_possible_score}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Начат</p>
          <p className="text-sm">{formatDate(lesson.started_at)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Завершён</p>
          <p className="text-sm">{formatDate(lesson.completed_at)}</p>
        </div>
      </div>

      {/* Таблица элементов */}
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12"></TableHead>
              <TableHead>Элемент</TableHead>
              <TableHead>Тип</TableHead>
              <TableHead>Статус</TableHead>
              <TableHead className="text-right">Баллы</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {elements.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  Нет элементов в этом уроке
                </TableCell>
              </TableRow>
            ) : (
              elements.map((element, index) => (
                <React.Fragment key={element.element_id}>
                  <TableRow
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => toggleElementExpansion(element.element_id)}
                  >
                    <TableCell>
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                        {expandedElements.has(element.element_id) ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </Button>
                    </TableCell>
                    <TableCell className="font-medium">
                      {index + 1}. {element.element_title}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {getElementTypeText(element.element_type)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {getStatusIcon(element.status)}
                        <span className="text-xs">{getStatusText(element.status)}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      {element.score !== null ? element.score : '-'}/{element.max_score}
                    </TableCell>
                  </TableRow>

                  {/* Развёрнутые детали */}
                  {expandedElements.has(element.element_id) && (
                    <TableRow>
                      <TableCell colSpan={5} className="bg-muted/30">
                        <ElementAnswerDetails element={element} formatDate={formatDate} />
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

// Компонент деталей ответа элемента
interface ElementAnswerDetailsProps {
  element: ElementProgressDetail;
  formatDate: (date: string | null) => string;
}

const ElementAnswerDetails: React.FC<ElementAnswerDetailsProps> = ({ element, formatDate }) => {
  return (
    <div className="p-4 space-y-3">
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-muted-foreground">Попытки:</span>{' '}
          <span className="font-medium">{element.attempts}</span>
        </div>
        <div>
          <span className="text-muted-foreground">Завершено:</span>{' '}
          <span className="font-medium">{formatDate(element.completed_at)}</span>
        </div>
      </div>

      {/* Ответ студента */}
      {element.student_answer && (
        <div className="space-y-2">
          <h5 className="font-semibold text-sm">Ответ студента:</h5>
          {element.element_type === 'text_problem' && (
            <div className="p-3 bg-background rounded border">
              <p className="text-sm whitespace-pre-wrap">
                {element.student_answer.text || 'Нет ответа'}
              </p>
            </div>
          )}
          {element.element_type === 'quick_question' && element.choices && (
            <div className="space-y-2">
              {element.choices.map((choice, idx) => {
                const isSelected = element.student_answer?.choice === idx;
                const isCorrect = element.correct_answer === idx;
                return (
                  <div
                    key={idx}
                    className={cn(
                      'p-2 rounded border text-sm',
                      isSelected && isCorrect && 'bg-green-100 border-green-500',
                      isSelected && !isCorrect && 'bg-red-100 border-red-500',
                      !isSelected && isCorrect && 'bg-green-50 border-green-300'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      {isSelected && <CheckCircle2 className="h-4 w-4" />}
                      {!isSelected && isCorrect && (
                        <span className="text-xs text-green-600">(правильный)</span>
                      )}
                      <span>{choice}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {element.element_type === 'theory' && (
            <p className="text-sm text-muted-foreground">
              {element.student_answer.viewed ? 'Материал просмотрен' : 'Не просмотрен'}
            </p>
          )}
          {element.element_type === 'video' && (
            <p className="text-sm text-muted-foreground">
              Просмотрено до {element.student_answer.watched_until || 0} секунд
            </p>
          )}
        </div>
      )}

      {!element.student_answer && (
        <p className="text-sm text-muted-foreground italic">Студент ещё не ответил</p>
      )}
    </div>
  );
};
