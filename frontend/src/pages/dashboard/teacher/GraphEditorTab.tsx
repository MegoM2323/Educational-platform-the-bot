/**
 * Teacher Graph Editor Tab
 * Визуальное редактирование графов знаний студентов
 */

import React, { useState, useCallback } from 'react';
import { useTeacherGraphEditor } from '@/hooks/useTeacherGraphEditor';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import {
  Eye,
  Edit3,
  Save,
  X,
  Undo,
  Redo,
  Plus,
  Trash2,
  Search,
  AlertCircle,
  Loader2,
  Users,
  BookOpen,
} from 'lucide-react';

interface GraphEditorTabProps {
  subjectId: number;
  subjectName?: string;
}

export const GraphEditorTab: React.FC<GraphEditorTabProps> = ({ subjectId, subjectName }) => {
  const { toast } = useToast();

  // Hook
  const {
    students,
    selectedStudent,
    graph,
    availableLessons,
    isLoadingStudents,
    isLoadingGraph,
    isLoadingLessons,
    isSaving,
    studentsError,
    graphError,
    lessonsError,
    editState,
    hasUnsavedChanges,
    selectStudent,
    addLesson,
    removeLesson,
    updateLessonPosition,
    addDependency,
    removeDependency,
    saveChanges,
    cancelChanges,
    undo,
    redo,
    canUndo,
    canRedo,
  } = useTeacherGraphEditor(subjectId);

  // Local state
  const [mode, setMode] = useState<'view' | 'edit'>('view');
  const [lessonBankOpen, setLessonBankOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Filtered lessons (not already in graph)
  const graphLessonIds = new Set(graph?.lessons.map((gl) => gl.lesson.id) || []);
  const filteredLessons = availableLessons.filter((lesson) => {
    if (graphLessonIds.has(lesson.id)) return false;
    if (!searchQuery) return true;
    return (
      lesson.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lesson.description.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  // Handlers
  const handleModeToggle = useCallback(() => {
    if (mode === 'edit' && hasUnsavedChanges) {
      const confirmed = window.confirm(
        'У вас есть несохранённые изменения. Вы уверены, что хотите выйти из режима редактирования?'
      );
      if (!confirmed) return;
      cancelChanges();
    }
    setMode((prev) => (prev === 'view' ? 'edit' : 'view'));
  }, [mode, hasUnsavedChanges, cancelChanges]);

  const handleSave = useCallback(async () => {
    try {
      await saveChanges();
      toast({
        title: 'Изменения сохранены',
        description: 'Граф знаний успешно обновлён',
      });
      setMode('view');
    } catch (error) {
      toast({
        title: 'Ошибка сохранения',
        description: error instanceof Error ? error.message : 'Не удалось сохранить изменения',
        variant: 'destructive',
      });
    }
  }, [saveChanges, toast]);

  const handleCancel = useCallback(() => {
    const confirmed = window.confirm(
      'Вы уверены, что хотите отменить все несохранённые изменения?'
    );
    if (confirmed) {
      cancelChanges();
      setMode('view');
    }
  }, [cancelChanges]);

  const handleAddLesson = useCallback(
    async (lessonId: number) => {
      try {
        // Calculate position for new lesson (center of viewport)
        const x = 400;
        const y = 300;
        await addLesson(lessonId, x, y);
        setLessonBankOpen(false);
        toast({
          title: 'Урок добавлен',
          description: 'Урок успешно добавлен в граф',
        });
      } catch (error) {
        toast({
          title: 'Ошибка',
          description: error instanceof Error ? error.message : 'Не удалось добавить урок',
          variant: 'destructive',
        });
      }
    },
    [addLesson, toast]
  );

  const handleRemoveLesson = useCallback(
    (graphLessonId: number) => {
      const confirmed = window.confirm('Вы уверены, что хотите удалить этот урок из графа?');
      if (confirmed) {
        removeLesson(graphLessonId);
        toast({
          title: 'Урок удалён',
          description: 'Урок будет удалён из графа после сохранения',
        });
      }
    },
    [removeLesson, toast]
  );

  // Loading state
  if (isLoadingStudents || isLoadingGraph || isLoadingLessons) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Загрузка...</span>
      </div>
    );
  }

  // Error state
  if (studentsError || graphError || lessonsError) {
    return (
      <div className="flex items-center justify-center h-96">
        <AlertCircle className="h-8 w-8 text-destructive" />
        <span className="ml-2 text-destructive">
          Ошибка загрузки: {studentsError?.message || graphError?.message || lessonsError?.message}
        </span>
      </div>
    );
  }

  // No students
  if (students.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Нет студентов</CardTitle>
          <CardDescription>
            У вас пока нет студентов для редактирования графов знаний
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Редактор графов знаний</h2>
          <p className="text-muted-foreground">
            {subjectName ? `Предмет: ${subjectName}` : 'Визуальное редактирование графов'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {mode === 'view' ? (
            <Button onClick={handleModeToggle} variant="default">
              <Edit3 className="h-4 w-4 mr-2" />
              Редактировать
            </Button>
          ) : (
            <>
              <Button onClick={handleCancel} variant="outline" disabled={isSaving}>
                <X className="h-4 w-4 mr-2" />
                Отмена
              </Button>
              <Button onClick={handleSave} disabled={!hasUnsavedChanges || isSaving}>
                {isSaving ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Save className="h-4 w-4 mr-2" />
                )}
                Сохранить
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Student selector */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Выбор студента
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Select
            value={selectedStudent?.id.toString()}
            onValueChange={(value) => {
              const student = students.find((s) => s.id.toString() === value);
              if (student) selectStudent(student);
            }}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Выберите студента" />
            </SelectTrigger>
            <SelectContent>
              {students.map((student) => (
                <SelectItem key={student.id} value={student.id.toString()}>
                  {student.full_name} ({student.email})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Edit toolbar (visible in edit mode) */}
      {mode === 'edit' && (
        <Card>
          <CardHeader>
            <CardTitle>Инструменты редактирования</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Dialog open={lessonBankOpen} onOpenChange={setLessonBankOpen}>
              <DialogTrigger asChild>
                <Button variant="outline">
                  <Plus className="h-4 w-4 mr-2" />
                  Добавить урок
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>Банк уроков</DialogTitle>
                  <DialogDescription>
                    Выберите уроки для добавления в граф знаний
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Поиск уроков..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                  <Separator />
                  <div className="space-y-2">
                    {filteredLessons.length === 0 ? (
                      <p className="text-center text-muted-foreground py-8">
                        {searchQuery ? 'Уроки не найдены' : 'Все уроки уже добавлены в граф'}
                      </p>
                    ) : (
                      filteredLessons.map((lesson) => (
                        <Card
                          key={lesson.id}
                          className="cursor-pointer hover:bg-accent transition-colors"
                          onClick={() => handleAddLesson(lesson.id)}
                        >
                          <CardContent className="p-4">
                            <div className="flex items-start justify-between">
                              <div className="space-y-1 flex-1">
                                <h4 className="font-semibold flex items-center gap-2">
                                  <BookOpen className="h-4 w-4" />
                                  {lesson.title}
                                </h4>
                                <p className="text-sm text-muted-foreground line-clamp-2">
                                  {lesson.description}
                                </p>
                                <div className="flex gap-2 mt-2">
                                  {lesson.elements_count !== undefined && (
                                    <Badge variant="outline">
                                      {lesson.elements_count} элементов
                                    </Badge>
                                  )}
                                  <Badge variant="outline">
                                    {lesson.total_duration_minutes} мин
                                  </Badge>
                                </div>
                              </div>
                              <Button type="button" size="sm" variant="ghost">
                                <Plus className="h-4 w-4" />
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      ))
                    )}
                  </div>
                </div>
              </DialogContent>
            </Dialog>

            <Button onClick={undo} variant="outline" disabled={!canUndo}>
              <Undo className="h-4 w-4 mr-2" />
              Отменить
            </Button>
            <Button onClick={redo} variant="outline" disabled={!canRedo}>
              <Redo className="h-4 w-4 mr-2" />
              Повторить
            </Button>

            {hasUnsavedChanges && (
              <Badge variant="destructive" className="ml-auto">
                Есть несохранённые изменения
              </Badge>
            )}
          </CardContent>
        </Card>
      )}

      {/* Graph visualization area */}
      <Card>
        <CardHeader>
          <CardTitle>График знаний</CardTitle>
          <CardDescription>
            {mode === 'view'
              ? 'Режим просмотра - переключитесь в режим редактирования для изменения графа'
              : 'Перетаскивайте уроки, создавайте связи между ними'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!graph || graph.lessons.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <BookOpen className="h-16 w-16 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">Граф пуст</h3>
              <p className="text-muted-foreground mb-4">
                {mode === 'edit'
                  ? 'Добавьте уроки из банка, чтобы начать создание графа знаний'
                  : 'Переключитесь в режим редактирования для добавления уроков'}
              </p>
              {mode === 'edit' && (
                <Button onClick={() => setLessonBankOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Добавить первый урок
                </Button>
              )}
            </div>
          ) : (
            <div className="border rounded-lg p-4 bg-muted/10 min-h-[500px]">
              <p className="text-center text-muted-foreground">
                Компонент GraphVisualization будет интегрирован из T503
              </p>
              <div className="mt-4 space-y-2">
                {graph.lessons.map((graphLesson) => (
                  <div
                    key={graphLesson.id}
                    className="flex items-center justify-between p-3 bg-background rounded border"
                  >
                    <div>
                      <p className="font-medium">{graphLesson.lesson.title}</p>
                      <p className="text-sm text-muted-foreground">
                        Позиция: ({graphLesson.position_x.toFixed(0)}, {graphLesson.position_y.toFixed(0)})
                      </p>
                    </div>
                    {mode === 'edit' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveLesson(graphLesson.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stats */}
      {graph && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Уроков в графе
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{graph.lessons.length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Зависимостей
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{graph.dependencies.length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Статус
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Badge variant={graph.is_active ? 'default' : 'secondary'}>
                {graph.is_active ? 'Активен' : 'Неактивен'}
              </Badge>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default GraphEditorTab;
