/**
 * Teacher Graph Editor Tab
 * Визуальное редактирование графов знаний студентов
 */

import React, { useState, useCallback, useEffect } from 'react';
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
  Link,
  Clock,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { GraphVisualization } from '@/components/knowledge-graph/GraphVisualization';
import type { GraphData, GraphNode, GraphLink } from '@/components/knowledge-graph/graph-types';
import type { KnowledgeGraph, GraphLesson } from '@/types/knowledgeGraph';

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

  // T004: Состояния для Node Click Action Menu
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedLessonForDetails, setSelectedLessonForDetails] = useState<GraphLesson | null>(null);
  const [showLessonDetailsDialog, setShowLessonDetailsDialog] = useState(false);

  // T005: Состояние для создания зависимости
  const [creatingDependencyFrom, setCreatingDependencyFrom] = useState<string | null>(null);

  // Преобразование данных графа для компонента GraphVisualization
  const transformToGraphData = useCallback((graphData: KnowledgeGraph | null): GraphData => {
    console.log('[GraphEditorTab] transformToGraphData called with:', graphData);

    if (!graphData) {
      console.log('[GraphEditorTab] No graph data, returning empty');
      return { nodes: [], links: [] };
    }

    // Защита от undefined/null массивов
    const lessons = Array.isArray(graphData.lessons) ? graphData.lessons : [];
    const dependencies = Array.isArray(graphData.dependencies) ? graphData.dependencies : [];

    console.log('[GraphEditorTab] Lessons count:', lessons.length);
    console.log('[GraphEditorTab] Dependencies count:', dependencies.length);
    console.log('[GraphEditorTab] Full lessons data:', lessons);
    console.log('[GraphEditorTab] Full dependencies data:', dependencies);

    const nodes: GraphNode[] = lessons
      .filter(gl => gl && gl.lesson)
      .map((gl, index) => {
        // Если позиция не задана, генерируем начальную позицию
        // используя круговую раскладку чтобы избежать наложения узлов
        let initialX = gl.position_x;
        let initialY = gl.position_y;

        if (initialX === null || initialX === undefined || initialY === null || initialY === undefined) {
          // Круговая раскладка с радиусом 200px вокруг центра (400, 300)
          const angle = (index / lessons.length) * 2 * Math.PI;
          const radius = 200;
          initialX = 400 + radius * Math.cos(angle);
          initialY = 300 + radius * Math.sin(angle);
        }

        return {
          id: gl.id.toString(),
          title: gl.lesson?.title || 'Без названия',
          status: gl.is_unlocked ? 'not_started' : 'locked',
          x: initialX,
          y: initialY,
        };
      });

    console.log('[GraphEditorTab] Transformed nodes:', nodes);

    const links: GraphLink[] = dependencies.map(dep => ({
      source: dep.from_lesson.toString(),
      target: dep.to_lesson.toString(),
      type: dep.dependency_type === 'prerequisite' ? 'prerequisite' : 'suggested',
    }));

    console.log('[GraphEditorTab] Transformed links:', links);

    const result = { nodes, links };
    console.log('[GraphEditorTab] Final GraphData:', result);
    return result;
  }, []);

  // Filtered lessons (not already in graph)
  // Защита от undefined - TanStack Query может вернуть undefined при ошибке
  const safeStudents = students || [];
  const safeAvailableLessons = availableLessons || [];

  // Безопасное извлечение ID уроков из графа
  const graphLessonIds = new Set(
    Array.isArray(graph?.lessons)
      ? graph.lessons.map(gl => gl?.lesson?.id).filter((id): id is number => id !== undefined)
      : []
  );

  const filteredLessons = safeAvailableLessons.filter((lesson) => {
    if (!lesson) return false;
    if (graphLessonIds.has(lesson.id)) return false;
    if (!searchQuery) return true;
    return (
      lesson.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lesson.description?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  // Обработчик перетаскивания узлов - обновляет позицию в локальном состоянии
  const handleNodeDrag = useCallback((nodeId: string, x: number, y: number) => {
    const graphLessonId = parseInt(nodeId, 10);
    if (!isNaN(graphLessonId)) {
      updateLessonPosition(graphLessonId, x, y);
    }
  }, [updateLessonPosition]);

  // T004: Обработчик клика по узлу
  const handleNodeClick = useCallback((nodeId: string) => {
    // Режим создания зависимости (T005)
    if (creatingDependencyFrom) {
      if (creatingDependencyFrom !== nodeId) {
        // Создаём зависимость: from -> to
        const fromGraphLessonId = parseInt(creatingDependencyFrom, 10);
        const toGraphLessonId = parseInt(nodeId, 10);
        if (!isNaN(fromGraphLessonId) && !isNaN(toGraphLessonId)) {
          addDependency(fromGraphLessonId, toGraphLessonId);
          toast({
            title: 'Зависимость добавлена',
            description: 'Связь будет сохранена после нажатия "Сохранить"',
          });
        }
      }
      setCreatingDependencyFrom(null);
      return;
    }

    if (mode === 'view') {
      // В режиме просмотра - показать детали урока
      const graphLesson = graph?.lessons?.find(gl => gl.id.toString() === nodeId);
      if (graphLesson) {
        setSelectedLessonForDetails(graphLesson);
        setShowLessonDetailsDialog(true);
      }
    } else {
      // В режиме редактирования - выбрать/отменить выбор узла
      setSelectedNodeId(prev => prev === nodeId ? null : nodeId);
    }
  }, [mode, graph, creatingDependencyFrom, addDependency, toast]);

  // T004: Сброс состояния при нажатии Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setCreatingDependencyFrom(null);
        setSelectedNodeId(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

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
  if (safeStudents.length === 0) {
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
              const student = safeStudents.find((s) => s.id.toString() === value);
              if (student) selectStudent(student);
            }}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Выберите студента" />
            </SelectTrigger>
            <SelectContent>
              {safeStudents.map((student) => (
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

                  {/* Состояние загрузки */}
                  {isLoadingLessons && (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin" />
                      <span className="ml-2 text-muted-foreground">Загрузка уроков...</span>
                    </div>
                  )}

                  {/* Состояние ошибки */}
                  {lessonsError && !isLoadingLessons && (
                    <div className="text-center py-8 text-destructive">
                      <AlertCircle className="h-8 w-8 mx-auto mb-2" />
                      <p className="font-medium">Ошибка загрузки уроков</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        {lessonsError instanceof Error ? lessonsError.message : 'Неизвестная ошибка'}
                      </p>
                    </div>
                  )}

                  {/* Состояние пустого списка */}
                  {!isLoadingLessons && !lessonsError && filteredLessons.length === 0 && (
                    <div className="text-center py-8 text-muted-foreground">
                      <BookOpen className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      {searchQuery ? (
                        <>
                          <p className="font-medium">Уроки не найдены</p>
                          <p className="text-sm mt-1">Попробуйте изменить поисковый запрос</p>
                        </>
                      ) : (
                        <>
                          <p className="font-medium">Нет доступных уроков для добавления</p>
                          <p className="text-sm mt-1">Все уроки уже добавлены в граф или нет созданных уроков</p>
                        </>
                      )}
                    </div>
                  )}

                  {/* Список уроков */}
                  {!isLoadingLessons && !lessonsError && filteredLessons.length > 0 && (
                    <div className="space-y-2 max-h-[400px] overflow-y-auto">
                      {filteredLessons.map((lesson) => (
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
                      ))}
                    </div>
                  )}
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
          {!graph || !Array.isArray(graph.lessons) || graph.lessons.length === 0 ? (
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
            <div className="relative">
              {/* PRODUCTION: Основной компонент графа */}
              <GraphVisualization
                data={transformToGraphData(graph)}
                isEditable={mode === 'edit'}
                onNodeClick={handleNodeClick}
                onNodeDrag={handleNodeDrag}
                width={800}
                height={600}
                showLegend={true}
              />

              {/* T004: Меню действий для выбранного узла в режиме редактирования */}
              {selectedNodeId && mode === 'edit' && (
                <Card className="absolute top-4 left-4 p-4 space-y-2 z-50 bg-white/95 backdrop-blur shadow-lg">
                  <p className="font-medium text-sm">Выбран урок</p>
                  <div className="flex flex-col gap-2">
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      onClick={() => {
                        handleRemoveLesson(parseInt(selectedNodeId, 10));
                        setSelectedNodeId(null);
                      }}
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Удалить из графа
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setCreatingDependencyFrom(selectedNodeId);
                        setSelectedNodeId(null);
                      }}
                    >
                      <Link className="h-4 w-4 mr-2" />
                      Создать связь
                    </Button>
                  </div>
                </Card>
              )}

              {/* T005: Индикатор режима создания зависимости */}
              {creatingDependencyFrom && (
                <Card className="absolute top-4 left-4 p-4 bg-yellow-50 border-yellow-200 z-50 shadow-lg">
                  <p className="font-medium text-yellow-800">
                    Режим создания связи
                  </p>
                  <p className="text-sm text-yellow-600 mt-1">
                    Выберите целевой урок (который зависит от выбранного)
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="mt-2"
                    onClick={() => setCreatingDependencyFrom(null)}
                  >
                    Отмена
                  </Button>
                </Card>
              )}
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
              <div className="text-2xl font-bold">{graph?.lessons?.length ?? 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Зависимостей
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{graph?.dependencies?.length ?? 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Статус
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Badge variant={graph?.is_active ? 'default' : 'secondary'}>
                {graph?.is_active ? 'Активен' : 'Неактивен'}
              </Badge>
            </CardContent>
          </Card>
        </div>
      )}

      {/* T006: Список зависимостей с кнопками удаления */}
      {mode === 'edit' && graph && Array.isArray(graph.dependencies) && graph.dependencies.length > 0 && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle className="text-lg">Зависимости</CardTitle>
            <CardDescription>Нажмите на иконку удаления чтобы убрать связь</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {graph.dependencies.map(dep => {
                const fromLesson = graph.lessons?.find(gl => gl.id === dep.from_lesson);
                const toLesson = graph.lessons?.find(gl => gl.id === dep.to_lesson);
                const isPendingRemoval = editState?.removedDependencies?.has(dep.id);

                return (
                  <li key={dep.id} className={`flex items-center justify-between p-2 rounded ${isPendingRemoval ? 'bg-red-50 line-through text-muted-foreground' : 'bg-muted/50'}`}>
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{fromLesson?.lesson?.title || 'Урок'}</span>
                      <ArrowRight className="h-4 w-4" />
                      <span className="font-medium">{toLesson?.lesson?.title || 'Урок'}</span>
                      <Badge variant="outline" className="ml-2">
                        {dep.dependency_type === 'prerequisite' || dep.dependency_type === 'required' ? 'Обязательная' : 'Рекомендуемая'}
                      </Badge>
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeDependency(dep.id)}
                      disabled={isPendingRemoval}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* T004: Диалог деталей урока (режим просмотра) */}
      <Dialog open={showLessonDetailsDialog} onOpenChange={setShowLessonDetailsDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              {selectedLessonForDetails?.lesson?.title || 'Урок'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-muted-foreground">
              {selectedLessonForDetails?.lesson?.description || 'Нет описания'}
            </p>
            <Separator />
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">
                  <span className="font-medium">Элементов:</span>{' '}
                  {selectedLessonForDetails?.lesson?.elements_count ?? 0}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">
                  <span className="font-medium">Время:</span>{' '}
                  {selectedLessonForDetails?.lesson?.total_duration_minutes ?? 0} мин
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={selectedLessonForDetails?.is_unlocked ? 'default' : 'secondary'}>
                {selectedLessonForDetails?.is_unlocked ? 'Разблокирован' : 'Заблокирован'}
              </Badge>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default GraphEditorTab;
