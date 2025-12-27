/**
 * Примеры использования ProgressViewerTab
 * Этот файл НЕ компилируется в production build
 */
import React, { useState } from 'react';
import { ProgressViewerTab } from './ProgressViewerTab';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// ============================================
// Пример 1: Базовое использование
// ============================================
export function Example1_BasicUsage() {
  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Прогресс студентов</h1>
      <ProgressViewerTab />
    </div>
  );
}

// ============================================
// Пример 2: С выбранным предметом
// ============================================
export function Example2_WithSubjectFilter() {
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | undefined>(1);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-bold">Прогресс по предмету</h1>
        <Select
          value={selectedSubjectId?.toString()}
          onValueChange={(value) => setSelectedSubjectId(Number(value))}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Выберите предмет" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1">Математика</SelectItem>
            <SelectItem value="2">Физика</SelectItem>
            <SelectItem value="3">Химия</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <ProgressViewerTab subjectId={selectedSubjectId} />
    </div>
  );
}

// ============================================
// Пример 3: Интеграция в Teacher Dashboard с табами
// ============================================
export function Example3_TeacherDashboardIntegration() {
  const [currentSubject, setCurrentSubject] = useState<number>(1);

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Кабинет преподавателя</h1>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Обзор</TabsTrigger>
          <TabsTrigger value="materials">Материалы</TabsTrigger>
          <TabsTrigger value="assignments">Задания</TabsTrigger>
          <TabsTrigger value="progress">Прогресс</TabsTrigger>
          <TabsTrigger value="reports">Отчёты</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <p>Обзор dashboard...</p>
        </TabsContent>

        <TabsContent value="materials" className="space-y-4">
          <p>Материалы...</p>
        </TabsContent>

        <TabsContent value="assignments" className="space-y-4">
          <p>Задания...</p>
        </TabsContent>

        <TabsContent value="progress" className="space-y-4">
          <ProgressViewerTab subjectId={currentSubject} />
        </TabsContent>

        <TabsContent value="reports" className="space-y-4">
          <p>Отчёты...</p>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ============================================
// Пример 4: С мультивыбором предметов
// ============================================
export function Example4_MultiSubjectView() {
  const subjects = [
    { id: 1, name: 'Математика' },
    { id: 2, name: 'Физика' },
    { id: 3, name: 'Химия' },
    { id: 4, name: 'Биология' },
  ];

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Прогресс по всем предметам</h1>

      <Tabs defaultValue="1" className="w-full">
        <TabsList>
          {subjects.map((subject) => (
            <TabsTrigger key={subject.id} value={subject.id.toString()}>
              {subject.name}
            </TabsTrigger>
          ))}
        </TabsList>

        {subjects.map((subject) => (
          <TabsContent key={subject.id} value={subject.id.toString()}>
            <ProgressViewerTab subjectId={subject.id} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

// ============================================
// Пример 5: Standalone страница
// ============================================
export function Example5_StandalonePage() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold">Мониторинг прогресса</h1>
          <p className="text-sm text-muted-foreground">
            Отслеживайте успеваемость ваших студентов
          </p>
        </div>
      </header>

      <main className="container mx-auto py-6">
        <ProgressViewerTab />
      </main>

      <footer className="border-t mt-12">
        <div className="container mx-auto px-4 py-4 text-center text-sm text-muted-foreground">
          THE_BOT Platform © 2025
        </div>
      </footer>
    </div>
  );
}

// ============================================
// Пример 6: С кастомными фильтрами (расширенный)
// ============================================
export function Example6_WithCustomFilters() {
  const [subjectId, setSubjectId] = useState<number>(1);
  const [dateRange, setDateRange] = useState<string>('all');

  return (
    <div className="p-4 space-y-6">
      <div className="flex flex-wrap gap-4 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="text-sm font-medium mb-2 block">Предмет</label>
          <Select value={subjectId.toString()} onValueChange={(v) => setSubjectId(Number(v))}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">Математика</SelectItem>
              <SelectItem value="2">Физика</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex-1 min-w-[200px]">
          <label className="text-sm font-medium mb-2 block">Период</label>
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Всё время</SelectItem>
              <SelectItem value="7days">Последние 7 дней</SelectItem>
              <SelectItem value="30days">Последние 30 дней</SelectItem>
              <SelectItem value="90days">Последние 90 дней</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <ProgressViewerTab subjectId={subjectId} />
    </div>
  );
}

// ============================================
// Export всех примеров для Storybook/тестирования
// ============================================
export const examples = {
  Example1_BasicUsage,
  Example2_WithSubjectFilter,
  Example3_TeacherDashboardIntegration,
  Example4_MultiSubjectView,
  Example5_StandalonePage,
  Example6_WithCustomFilters,
};

export default examples;
