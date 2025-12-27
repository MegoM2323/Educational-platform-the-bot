import React, { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useKnowledgeGraph, useStudentSubjects } from '@/hooks/useKnowledgeGraph';
import { GraphVisualization } from '@/components/knowledge-graph/GraphVisualization';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import {
  AlertCircle,
  RefreshCw,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Info,
  BookOpen,
  CheckCircle,
  Lock,
  PlayCircle,
} from 'lucide-react';
import { GraphData } from '@/components/knowledge-graph/graph-types';
import { KnowledgeGraph } from '@/integrations/api/knowledgeGraphAPI';
import { useProfile } from '@/hooks/useProfile';

/**
 * Student Knowledge Graph Tab Page
 *
 * Features:
 * - Subject selector (if student has multiple subjects)
 * - Visual knowledge graph with D3.js
 * - Progress indicators (colors, percentages)
 * - Lesson click navigation
 * - Lock/unlock based on dependencies
 * - Loading and error states
 * - Empty state handling
 * - Responsive design
 */
export const KnowledgeGraphTab: React.FC = () => {
  const navigate = useNavigate();
  const { profile } = useProfile();
  const studentId = profile?.id ?? null;

  // State
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | null>(null);

  // Fetch subjects and graph
  const { data: subjects, isLoading: subjectsLoading, error: subjectsError } = useStudentSubjects();
  const {
    data: graphData,
    isLoading: graphLoading,
    error: graphError,
    refreshGraph,
  } = useKnowledgeGraph(studentId, selectedSubjectId);

  // Auto-select first subject if only one available
  React.useEffect(() => {
    if (subjects && subjects.length === 1 && !selectedSubjectId) {
      setSelectedSubjectId(subjects[0].id);
    }
  }, [subjects, selectedSubjectId]);

  // Transform graph data for GraphVisualization component
  const visualizationData: GraphData | null = useMemo(() => {
    if (!graphData) return null;

    return {
      nodes: graphData.lessons.map((lesson) => ({
        id: String(lesson.lesson_id),
        title: lesson.title,
        status: lesson.status,
        x: lesson.position_x,
        y: lesson.position_y,
      })),
      links: graphData.dependencies.map((dep) => ({
        source: String(dep.from_lesson_id),
        target: String(dep.to_lesson_id),
        type: dep.type,
      })),
    };
  }, [graphData]);

  // Handle lesson click - navigate to lesson viewer
  const handleLessonClick = useCallback(
    (lessonId: string) => {
      const lesson = graphData?.lessons.find((l) => String(l.lesson_id) === lessonId);
      if (!lesson) return;

      // Check if lesson is locked
      if (lesson.status === 'locked' || !lesson.can_start) {
        // Show alert that prerequisites are not met
        alert('Этот урок заблокирован. Сначала завершите предыдущие уроки.');
        return;
      }

      // Navigate to lesson viewer
      navigate(`/lessons/${lessonId}`);
    },
    [graphData, navigate]
  );

  // Handle subject change
  const handleSubjectChange = (subjectId: string) => {
    setSelectedSubjectId(Number(subjectId));
  };

  // Handle refresh
  const handleRefresh = () => {
    refreshGraph();
  };

  // Loading state
  if (subjectsLoading || (graphLoading && selectedSubjectId)) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  // Error state
  if (subjectsError || graphError) {
    return (
      <Alert variant="destructive" className="m-4">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Ошибка загрузки графа знаний: {subjectsError?.message || graphError?.message}
          <Button variant="outline" size="sm" onClick={handleRefresh} className="ml-4">
            <RefreshCw className="h-4 w-4 mr-2" />
            Повторить
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  // No subjects state
  if (!subjects || subjects.length === 0) {
    return (
      <Card className="m-4">
        <CardHeader>
          <CardTitle>Граф знаний</CardTitle>
          <CardDescription>Визуализация вашего учебного прогресса</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              У вас пока нет зачисленных предметов. Обратитесь к вашему преподавателю.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  // No subject selected state
  if (!selectedSubjectId) {
    return (
      <Card className="m-4">
        <CardHeader>
          <CardTitle>Граф знаний</CardTitle>
          <CardDescription>Визуализация вашего учебного прогресса</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Выберите предмет:</label>
            <Select onValueChange={handleSubjectChange}>
              <SelectTrigger>
                <SelectValue placeholder="Выберите предмет" />
              </SelectTrigger>
              <SelectContent>
                {subjects.map((subject) => (
                  <SelectItem key={subject.id} value={String(subject.id)}>
                    {subject.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Empty graph state (no lessons in graph)
  if (graphData && graphData.lessons.length === 0) {
    return (
      <Card className="m-4">
        <CardHeader>
          <CardTitle>Граф знаний</CardTitle>
          <CardDescription>{graphData.subject_name}</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              В графе знаний пока нет уроков. Ваш преподаватель скоро добавит учебные материалы.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  // Main render
  return (
    <div className="flex flex-col gap-4 p-4 h-full">
      {/* Header with subject selector and stats */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div className="flex-1">
              <CardTitle>Граф знаний</CardTitle>
              <CardDescription>
                {graphData?.subject_name || 'Выберите предмет'}
              </CardDescription>
            </div>

            {/* Subject selector (if multiple subjects) */}
            {subjects.length > 1 && (
              <div className="w-full sm:w-64">
                <Select value={String(selectedSubjectId)} onValueChange={handleSubjectChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {subjects.map((subject) => (
                      <SelectItem key={subject.id} value={String(subject.id)}>
                        {subject.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Progress summary */}
          {graphData && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="font-medium">Общий прогресс:</span>
                <span className="text-muted-foreground">
                  {graphData.completed_lessons} из {graphData.total_lessons} уроков завершено
                </span>
              </div>
              <Progress value={graphData.overall_progress_percent} className="h-2" />
              <p className="text-sm text-muted-foreground text-center">
                {Math.round(graphData.overall_progress_percent)}%
              </p>
            </div>
          )}

          {/* Refresh button */}
          <div className="flex justify-end">
            <Button variant="outline" size="sm" onClick={handleRefresh}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Обновить
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Legend */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full bg-gray-300" />
              <span className="text-sm">Не начато</span>
            </div>
            <div className="flex items-center gap-2">
              <PlayCircle className="w-4 h-4 text-blue-500" />
              <span className="text-sm">В процессе</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span className="text-sm">Завершено</span>
            </div>
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-red-500" />
              <span className="text-sm">Заблокировано</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Graph Visualization */}
      <Card className="flex-1 min-h-[500px]">
        <CardContent className="p-0 h-full">
          {visualizationData && (
            <GraphVisualization
              data={visualizationData}
              onNodeClick={handleLessonClick}
              isEditable={false}
              className="w-full h-full"
            />
          )}
        </CardContent>
      </Card>

      {/* Help text */}
      <Card>
        <CardContent className="pt-6">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              <strong>Как использовать граф знаний:</strong>
              <ul className="list-disc list-inside mt-2 space-y-1 text-sm">
                <li>Нажмите на урок, чтобы открыть его</li>
                <li>Серые уроки доступны для начала</li>
                <li>Синие уроки - в процессе выполнения</li>
                <li>Зелёные уроки - завершены</li>
                <li>Красные уроки - заблокированы (нужно выполнить предыдущие)</li>
                <li>Используйте колёсико мыши для масштабирования</li>
                <li>Перетаскивайте граф для навигации</li>
              </ul>
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    </div>
  );
};
