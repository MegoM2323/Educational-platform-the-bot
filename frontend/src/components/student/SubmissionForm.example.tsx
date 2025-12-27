/**
 * SubmissionForm Component - Usage Examples
 *
 * This file demonstrates how to use the SubmissionForm component
 * in different scenarios.
 */

import { useState } from 'react';
import { SubmissionForm } from './SubmissionForm';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

/**
 * Example 1: Basic usage in a modal dialog
 */
export function SubmissionFormModalExample() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setOpen(true)}>Отправить ответ</Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Отправка ответа на задание</DialogTitle>
          </DialogHeader>
          <SubmissionForm
            materialId={123}
            materialTitle="Решение квадратных уравнений"
            onSuccess={() => {
              setOpen(false);
              console.log('Submission successful');
            }}
            onCancel={() => setOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}

/**
 * Example 2: Inline form on a page
 */
export function SubmissionFormPageExample() {
  const handleSuccess = (submissionId?: string | number) => {
    console.log('Successfully submitted assignment with ID:', submissionId);
    // Redirect to success page or show confirmation
  };

  return (
    <div className="container max-w-2xl py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Задание: Анализ литературного произведения</h1>
        <p className="text-muted-foreground mt-2">
          Срок сдачи: 15 января 2025 г.
        </p>
      </div>

      <SubmissionForm
        materialId={456}
        materialTitle="Анализ литературного произведения"
        onSuccess={handleSuccess}
      />
    </div>
  );
}

/**
 * Example 3: With custom styling
 */
export function SubmissionFormStyledExample() {
  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-slate-900 dark:to-slate-800 p-8 rounded-lg">
      <SubmissionForm
        materialId={789}
        materialTitle="Проектная работа по физике"
        className="shadow-lg"
        onSuccess={(submissionId) => {
          alert(`Спасибо! Ваш ответ с ID ${submissionId} успешно отправлен.`);
        }}
        onCancel={() => {
          console.log('Form cancelled');
        }}
      />
    </div>
  );
}

/**
 * Example 4: With integration to page state
 */
export function SubmissionFormIntegratedExample() {
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [submissionId, setSubmissionId] = useState<string | number | null>(null);

  if (isSubmitted) {
    return (
      <div className="p-8 bg-green-50 dark:bg-green-950/20 rounded-lg border border-green-200 dark:border-green-900/50">
        <h2 className="text-2xl font-bold text-green-900 dark:text-green-200">
          Ответ успешно отправлен!
        </h2>
        <p className="text-green-800 dark:text-green-300 mt-2">
          ID вашего ответа: <code className="bg-green-100 dark:bg-green-900/50 px-2 py-1 rounded">{submissionId}</code>
        </p>
        <p className="text-green-700 dark:text-green-400 mt-4">
          Преподаватель проверит ваш ответ и оставит обратную связь в течение 3-5 дней.
        </p>
      </div>
    );
  }

  return (
    <SubmissionForm
      materialId={999}
      materialTitle="Итоговый контрольный тест"
      onSuccess={(id) => {
        setSubmissionId(id);
        setIsSubmitted(true);
      }}
    />
  );
}

/**
 * Example 5: Assignment submission with deadline
 */
export function AssignmentSubmissionExample() {
  const assignment = {
    id: 111,
    title: 'Написать эссе "Роль искусства в обществе"',
    description: 'Напишите эссе объемом 800-1200 слов на тему роли искусства в современном обществе.',
    deadline: new Date(2025, 0, 20), // Jan 20, 2025
    maxScore: 100,
  };

  const isOverdue = new Date() > assignment.deadline;
  const daysLeft = Math.ceil(
    (assignment.deadline.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)
  );

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 dark:bg-blue-950/20 p-6 rounded-lg border border-blue-200 dark:border-blue-900/50">
        <h1 className="text-2xl font-bold">{assignment.title}</h1>
        <p className="text-foreground/70 mt-2">{assignment.description}</p>

        <div className="grid grid-cols-2 gap-4 mt-4">
          <div>
            <p className="text-sm font-semibold text-foreground/60">Срок сдачи</p>
            <p className={`text-lg font-bold ${isOverdue ? 'text-red-600' : 'text-green-600'}`}>
              {assignment.deadline.toLocaleDateString('ru-RU', {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground/60">Время</p>
            <p className={`text-lg font-bold ${isOverdue ? 'text-red-600' : 'text-green-600'}`}>
              {isOverdue ? 'Просрочено' : `${daysLeft} дней`}
            </p>
          </div>
        </div>
      </div>

      {isOverdue && (
        <div className="bg-yellow-50 dark:bg-yellow-950/20 p-4 rounded-lg border border-yellow-200 dark:border-yellow-900/50">
          <p className="text-yellow-800 dark:text-yellow-200">
            Внимание: срок сдачи истекл. Отправка запоздалого ответа может повлиять на оценку.
          </p>
        </div>
      )}

      <SubmissionForm
        materialId={assignment.id}
        materialTitle={assignment.title}
        onSuccess={(submissionId) => {
          console.log('Assignment submitted:', submissionId);
        }}
      />
    </div>
  );
}
