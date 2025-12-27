/**
 * Content Creator Tab
 * Управление элементами и уроками (T604)
 */
import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Plus,
  Search,
  Grid3x3,
  List,
  Edit,
  Copy,
  Trash2,
  Eye,
  EyeOff,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { useContentCreator } from '@/hooks/useContentCreator';
import { ElementListItem, LessonListItem } from '@/services/contentCreatorService';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

interface ContentCreatorTabProps {
  onCreateElement?: () => void;
  onEditElement?: (id: number) => void;
  onCreateLesson?: () => void;
  onEditLesson?: (id: number) => void;
}

const elementTypeLabels: Record<string, string> = {
  text_problem: 'Текстовая задача',
  quick_question: 'Быстрый вопрос',
  theory: 'Теория',
  video: 'Видео',
};

export const ContentCreatorTab: React.FC<ContentCreatorTabProps> = ({
  onCreateElement,
  onEditElement,
  onCreateLesson,
  onEditLesson,
}) => {
  const {
    elements,
    elementsCount,
    elementsLoading,
    lessons,
    lessonsCount,
    lessonsLoading,
    elementFilters,
    setElementFilters,
    lessonFilters,
    setLessonFilters,
    selectedElements,
    selectedLessons,
    toggleElementSelection,
    toggleLessonSelection,
    clearElementSelection,
    clearLessonSelection,
    deleteElement,
    deleteLesson,
    copyElement,
    copyLesson,
    bulkDeleteElements,
    bulkDeleteLessons,
    isDeleting,
  } = useContentCreator();

  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<{
    type: 'element' | 'lesson';
    id: number;
    title: string;
  } | null>(null);
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);
  const [bulkDeleteType, setBulkDeleteType] = useState<'elements' | 'lessons'>('elements');

  // ============================================
  // Handlers
  // ============================================

  const handleDeleteClick = (type: 'element' | 'lesson', id: number, title: string) => {
    setItemToDelete({ type, id, title });
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = () => {
    if (!itemToDelete) return;

    if (itemToDelete.type === 'element') {
      deleteElement(itemToDelete.id);
    } else {
      deleteLesson(itemToDelete.id);
    }

    setDeleteDialogOpen(false);
    setItemToDelete(null);
  };

  const handleBulkDeleteClick = (type: 'elements' | 'lessons') => {
    setBulkDeleteType(type);
    setBulkDeleteDialogOpen(true);
  };

  const handleConfirmBulkDelete = async () => {
    if (bulkDeleteType === 'elements') {
      await bulkDeleteElements();
    } else {
      await bulkDeleteLessons();
    }
    setBulkDeleteDialogOpen(false);
  };

  const handleCopyElement = (id: number) => {
    copyElement(id);
  };

  const handleCopyLesson = (id: number) => {
    copyLesson(id);
  };

  // ============================================
  // Elements Tab Content
  // ============================================

  const renderElementsContent = () => (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4">
        <Button
          type="button"
          onClick={onCreateElement}
          className="gradient-primary shadow-glow"
        >
          <Plus className="w-4 h-4 mr-2" />
          Создать элемент
        </Button>

        <div className="flex-1 flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Поиск по названию или описанию..."
              value={elementFilters.search}
              onChange={(e) =>
                setElementFilters({ ...elementFilters, search: e.target.value, page: 1 })
              }
              className="pl-10"
            />
          </div>

          <Select
            value={elementFilters.type || 'all'}
            onValueChange={(value) =>
              setElementFilters({
                ...elementFilters,
                type: value === 'all' ? undefined : value,
                page: 1,
              })
            }
          >
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="Тип элемента" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все типы</SelectItem>
              <SelectItem value="text_problem">Текстовая задача</SelectItem>
              <SelectItem value="quick_question">Быстрый вопрос</SelectItem>
              <SelectItem value="theory">Теория</SelectItem>
              <SelectItem value="video">Видео</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={elementFilters.visibility}
            onValueChange={(value: 'mine' | 'all') =>
              setElementFilters({ ...elementFilters, visibility: value, page: 1 })
            }
          >
            <SelectTrigger className="w-full sm:w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="mine">Мои элементы</SelectItem>
              <SelectItem value="all">Все элементы</SelectItem>
            </SelectContent>
          </Select>

          <div className="flex gap-2">
            <Button
              type="button"
              variant={viewMode === 'list' ? 'default' : 'outline'}
              size="icon"
              onClick={() => setViewMode('list')}
            >
              <List className="w-4 h-4" />
            </Button>
            <Button
              type="button"
              variant={viewMode === 'grid' ? 'default' : 'outline'}
              size="icon"
              onClick={() => setViewMode('grid')}
            >
              <Grid3x3 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedElements.size > 0 && (
        <Card className="p-4 bg-muted">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">
              Выбрано: {selectedElements.size}
            </span>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={clearElementSelection}
              >
                Отменить выбор
              </Button>
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={() => handleBulkDeleteClick('elements')}
                disabled={isDeleting}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Удалить выбранные
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Loading */}
      {elementsLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!elementsLoading && elements.length === 0 && (
        <Card className="p-8">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-medium mb-2">Элементы не найдены</h3>
            <p className="text-muted-foreground mb-4">
              {elementFilters.visibility === 'mine'
                ? 'Вы еще не создали ни одного элемента'
                : 'Нет элементов, соответствующих критериям поиска'}
            </p>
            <Button type="button" onClick={onCreateElement}>
              <Plus className="w-4 h-4 mr-2" />
              Создать первый элемент
            </Button>
          </div>
        </Card>
      )}

      {/* List View */}
      {!elementsLoading && elements.length > 0 && viewMode === 'list' && (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12"></TableHead>
                <TableHead>Название</TableHead>
                <TableHead>Тип</TableHead>
                <TableHead>Время (мин)</TableHead>
                <TableHead>Создано</TableHead>
                <TableHead className="w-32">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {elements.map((element) => (
                <TableRow key={element.id}>
                  <TableCell>
                    <Checkbox
                      checked={selectedElements.has(element.id)}
                      onCheckedChange={() => toggleElementSelection(element.id)}
                    />
                  </TableCell>
                  <TableCell>
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        {element.title}
                        {element.is_public ? (
                          <Eye className="w-3 h-3 text-muted-foreground" />
                        ) : (
                          <EyeOff className="w-3 h-3 text-muted-foreground" />
                        )}
                      </div>
                      {element.description && (
                        <div className="text-sm text-muted-foreground line-clamp-1">
                          {element.description}
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {elementTypeLabels[element.element_type] || element.element_type}
                    </Badge>
                  </TableCell>
                  <TableCell>{element.estimated_time_minutes || '—'}</TableCell>
                  <TableCell>
                    {format(new Date(element.created_at), 'dd MMM yyyy', { locale: ru })}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => onEditElement?.(element.id)}
                        title="Редактировать"
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => handleCopyElement(element.id)}
                        title="Копировать"
                      >
                        <Copy className="w-4 h-4" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          handleDeleteClick('element', element.id, element.title)
                        }
                        title="Удалить"
                      >
                        <Trash2 className="w-4 h-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Grid View */}
      {!elementsLoading && elements.length > 0 && viewMode === 'grid' && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {elements.map((element) => (
            <Card key={element.id} className="p-4 hover:border-primary transition-colors">
              <div className="flex items-start justify-between mb-3">
                <Checkbox
                  checked={selectedElements.has(element.id)}
                  onCheckedChange={() => toggleElementSelection(element.id)}
                />
                <div className="flex gap-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => onEditElement?.(element.id)}
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => handleCopyElement(element.id)}
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeleteClick('element', element.id, element.title)}
                  >
                    <Trash2 className="w-4 h-4 text-destructive" />
                  </Button>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium line-clamp-1">{element.title}</h3>
                  {element.is_public ? (
                    <Eye className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                  ) : (
                    <EyeOff className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                  )}
                </div>
                {element.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {element.description}
                  </p>
                )}
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant="outline">
                    {elementTypeLabels[element.element_type] || element.element_type}
                  </Badge>
                  {element.estimated_time_minutes && (
                    <Badge variant="secondary">{element.estimated_time_minutes} мин</Badge>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  {format(new Date(element.created_at), 'dd MMM yyyy', { locale: ru })}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination info */}
      {!elementsLoading && elements.length > 0 && (
        <div className="text-sm text-muted-foreground text-center">
          Показано {elements.length} из {elementsCount}
        </div>
      )}
    </div>
  );

  // ============================================
  // Lessons Tab Content
  // ============================================

  const renderLessonsContent = () => (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4">
        <Button
          type="button"
          onClick={onCreateLesson}
          className="gradient-primary shadow-glow"
        >
          <Plus className="w-4 h-4 mr-2" />
          Создать урок
        </Button>

        <div className="flex-1 flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Поиск по названию или описанию..."
              value={lessonFilters.search}
              onChange={(e) =>
                setLessonFilters({ ...lessonFilters, search: e.target.value, page: 1 })
              }
              className="pl-10"
            />
          </div>

          <Select
            value={lessonFilters.visibility}
            onValueChange={(value: 'mine' | 'all') =>
              setLessonFilters({ ...lessonFilters, visibility: value, page: 1 })
            }
          >
            <SelectTrigger className="w-full sm:w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="mine">Мои уроки</SelectItem>
              <SelectItem value="all">Все уроки</SelectItem>
            </SelectContent>
          </Select>

          <div className="flex gap-2">
            <Button
              type="button"
              variant={viewMode === 'list' ? 'default' : 'outline'}
              size="icon"
              onClick={() => setViewMode('list')}
            >
              <List className="w-4 h-4" />
            </Button>
            <Button
              type="button"
              variant={viewMode === 'grid' ? 'default' : 'outline'}
              size="icon"
              onClick={() => setViewMode('grid')}
            >
              <Grid3x3 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedLessons.size > 0 && (
        <Card className="p-4 bg-muted">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Выбрано: {selectedLessons.size}</span>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={clearLessonSelection}
              >
                Отменить выбор
              </Button>
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={() => handleBulkDeleteClick('lessons')}
                disabled={isDeleting}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Удалить выбранные
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Loading */}
      {lessonsLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!lessonsLoading && lessons.length === 0 && (
        <Card className="p-8">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-medium mb-2">Уроки не найдены</h3>
            <p className="text-muted-foreground mb-4">
              {lessonFilters.visibility === 'mine'
                ? 'Вы еще не создали ни одного урока'
                : 'Нет уроков, соответствующих критериям поиска'}
            </p>
            <Button type="button" onClick={onCreateLesson}>
              <Plus className="w-4 h-4 mr-2" />
              Создать первый урок
            </Button>
          </div>
        </Card>
      )}

      {/* List View */}
      {!lessonsLoading && lessons.length > 0 && viewMode === 'list' && (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12"></TableHead>
                <TableHead>Название</TableHead>
                <TableHead>Элементов</TableHead>
                <TableHead>Время (мин)</TableHead>
                <TableHead>Создано</TableHead>
                <TableHead className="w-32">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {lessons.map((lesson) => (
                <TableRow key={lesson.id}>
                  <TableCell>
                    <Checkbox
                      checked={selectedLessons.has(lesson.id)}
                      onCheckedChange={() => toggleLessonSelection(lesson.id)}
                    />
                  </TableCell>
                  <TableCell>
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        {lesson.title}
                        {lesson.is_public ? (
                          <Eye className="w-3 h-3 text-muted-foreground" />
                        ) : (
                          <EyeOff className="w-3 h-3 text-muted-foreground" />
                        )}
                      </div>
                      {lesson.description && (
                        <div className="text-sm text-muted-foreground line-clamp-1">
                          {lesson.description}
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>{lesson.elements_count}</TableCell>
                  <TableCell>{lesson.total_duration_minutes || '—'}</TableCell>
                  <TableCell>
                    {format(new Date(lesson.created_at), 'dd MMM yyyy', { locale: ru })}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => onEditLesson?.(lesson.id)}
                        title="Редактировать"
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => handleCopyLesson(lesson.id)}
                        title="Копировать"
                      >
                        <Copy className="w-4 h-4" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteClick('lesson', lesson.id, lesson.title)}
                        title="Удалить"
                      >
                        <Trash2 className="w-4 h-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Grid View */}
      {!lessonsLoading && lessons.length > 0 && viewMode === 'grid' && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {lessons.map((lesson) => (
            <Card key={lesson.id} className="p-4 hover:border-primary transition-colors">
              <div className="flex items-start justify-between mb-3">
                <Checkbox
                  checked={selectedLessons.has(lesson.id)}
                  onCheckedChange={() => toggleLessonSelection(lesson.id)}
                />
                <div className="flex gap-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => onEditLesson?.(lesson.id)}
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => handleCopyLesson(lesson.id)}
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeleteClick('lesson', lesson.id, lesson.title)}
                  >
                    <Trash2 className="w-4 h-4 text-destructive" />
                  </Button>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium line-clamp-1">{lesson.title}</h3>
                  {lesson.is_public ? (
                    <Eye className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                  ) : (
                    <EyeOff className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                  )}
                </div>
                {lesson.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {lesson.description}
                  </p>
                )}
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant="outline">{lesson.elements_count} элементов</Badge>
                  {lesson.total_duration_minutes && (
                    <Badge variant="secondary">{lesson.total_duration_minutes} мин</Badge>
                  )}
                  {lesson.total_max_score && (
                    <Badge variant="secondary">{lesson.total_max_score} баллов</Badge>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  {format(new Date(lesson.created_at), 'dd MMM yyyy', { locale: ru })}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination info */}
      {!lessonsLoading && lessons.length > 0 && (
        <div className="text-sm text-muted-foreground text-center">
          Показано {lessons.length} из {lessonsCount}
        </div>
      )}
    </div>
  );

  // ============================================
  // Main Render
  // ============================================

  return (
    <>
      <Tabs defaultValue="elements" className="w-full">
        <TabsList className="grid w-full grid-cols-2 max-w-md">
          <TabsTrigger value="elements">Элементы</TabsTrigger>
          <TabsTrigger value="lessons">Уроки</TabsTrigger>
        </TabsList>

        <TabsContent value="elements" className="mt-6">
          {renderElementsContent()}
        </TabsContent>

        <TabsContent value="lessons" className="mt-6">
          {renderLessonsContent()}
        </TabsContent>
      </Tabs>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Подтвердите удаление</AlertDialogTitle>
            <AlertDialogDescription>
              Вы уверены, что хотите удалить{' '}
              <strong>{itemToDelete?.title}</strong>?
              <br />
              Это действие нельзя отменить.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={isDeleting}
            >
              {isDeleting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Удаление...
                </>
              ) : (
                'Удалить'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Bulk Delete Confirmation Dialog */}
      <AlertDialog open={bulkDeleteDialogOpen} onOpenChange={setBulkDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Подтвердите массовое удаление</AlertDialogTitle>
            <AlertDialogDescription>
              Вы уверены, что хотите удалить{' '}
              {bulkDeleteType === 'elements'
                ? `${selectedElements.size} элементов`
                : `${selectedLessons.size} уроков`}
              ?
              <br />
              Это действие нельзя отменить.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmBulkDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={isDeleting}
            >
              {isDeleting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Удаление...
                </>
              ) : (
                'Удалить всё'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};
