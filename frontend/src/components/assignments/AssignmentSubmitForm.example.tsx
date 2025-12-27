/**
 * Example usage of AssignmentSubmitForm component
 * This file demonstrates various ways to use the assignment submission form.
 */

import React, { useState } from 'react';
import { AssignmentSubmitForm } from './AssignmentSubmitForm';
import { Assignment } from '@/integrations/api/assignmentsAPI';

// Example 1: Simple submission form
export const SimpleSubmissionExample: React.FC = () => {
  const mockAssignment: Assignment = {
    id: 1,
    title: 'Итоговое эссе по истории',
    description: 'Напишите эссе на тему влияния Французской революции на современное общество',
    instructions: `
      1. Объем: 1500-2000 слов
      2. Структура: введение, основная часть (3-4 параграфа), заключение
      3. Цитируйте не менее 5 источников
      4. Используйте научный стиль
    `,
    type: 'essay',
    status: 'published',
    max_score: 100,
    attempts_limit: 2,
    start_date: new Date().toISOString(),
    due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days from now
    tags: 'история,эссе,литература',
    difficulty_level: 3,
    author: {
      id: 1,
      email: 'teacher@example.com',
      full_name: 'Иван Петров',
    },
    assigned_to: [1, 2, 3],
    is_overdue: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const handleSubmit = async (data: any, files: File[]) => {
    console.log('Submitted:', { data, files });
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 2000));
  };

  return (
    <AssignmentSubmitForm
      assignment={mockAssignment}
      questionCount={0}
      onSubmit={handleSubmit}
      showConfirmation={false}
    />
  );
};

// Example 2: Form with quiz questions
export const QuizSubmissionExample: React.FC = () => {
  const mockAssignment: Assignment = {
    id: 2,
    title: 'Тест по математике',
    description: 'Решите задачи из пройденного материала',
    instructions: `
      Вам предлагается 4 задачи разного уровня сложности.
      Решите все задачи и загрузите фото решений или напишите ответы в форме.
    `,
    type: 'test',
    status: 'published',
    max_score: 40,
    time_limit: 60, // 60 minutes
    attempts_limit: 3,
    start_date: new Date().toISOString(),
    due_date: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
    tags: 'математика,алгебра,геометрия',
    difficulty_level: 2,
    author: {
      id: 2,
      email: 'math-teacher@example.com',
      full_name: 'Мария Сидорова',
    },
    assigned_to: [1, 2, 3, 4],
    is_overdue: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (data: any, files: File[]) => {
    setIsLoading(true);
    try {
      console.log('Quiz submission:', { data, files });
      // API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AssignmentSubmitForm
      assignment={mockAssignment}
      questionCount={4}
      onSubmit={handleSubmit}
      isLoading={isLoading}
      showConfirmation={true}
    />
  );
};

// Example 3: Form with project submission
export const ProjectSubmissionExample: React.FC = () => {
  const mockAssignment: Assignment = {
    id: 3,
    title: 'Групповой проект: Веб-приложение',
    description: 'Создайте веб-приложение с использованием React и Node.js',
    instructions: `
      Требования проекта:
      - Использовать React 18+
      - Реализовать минимум 3 страницы
      - Добавить аутентификацию пользователей
      - Написать минимум 80% тестов
      - Задеплоить на GitHub Pages или Vercel

      Загрузите:
      1. Ссылку на репозиторий GitHub
      2. Ссылку на живое приложение
      3. Документацию в PDF
    `,
    type: 'project',
    status: 'published',
    max_score: 100,
    attempts_limit: 1,
    start_date: new Date().toISOString(),
    due_date: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(),
    tags: 'web,react,javascript,проект',
    difficulty_level: 4,
    author: {
      id: 3,
      email: 'senior@example.com',
      full_name: 'Алексей Иванов',
    },
    assigned_to: [1, 2],
    is_overdue: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const handleSubmit = async (data: any, files: File[]) => {
    console.log('Project submission:', { data, files });
    // API call - upload project files
  };

  return (
    <AssignmentSubmitForm
      assignment={mockAssignment}
      onSubmit={handleSubmit}
      showConfirmation={true}
    />
  );
};

// Example 4: Form with validation display
export const ValidationExample: React.FC = () => {
  const mockAssignment: Assignment = {
    id: 4,
    title: 'Обязательное задание',
    description: 'Это задание имеет строгие ограничения по времени и попыткам',
    instructions: 'Выполните все требования тщательно',
    type: 'homework',
    status: 'published',
    max_score: 50,
    time_limit: 30,
    attempts_limit: 1,
    start_date: new Date().toISOString(),
    due_date: new Date(Date.now() + 1 * 24 * 60 * 60 * 1000).toISOString(),
    tags: 'homework',
    difficulty_level: 2,
    author: {
      id: 1,
      email: 'teacher@example.com',
      full_name: 'Иван Петров',
    },
    assigned_to: [1],
    is_overdue: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const handleSubmit = async (data: any, files: File[]) => {
    // Validation example
    if (!data.notes.trim() && files.length === 0) {
      throw new Error('Заполните хотя бы одно поле');
    }
    console.log('Validated submission:', { data, files });
  };

  return (
    <AssignmentSubmitForm
      assignment={mockAssignment}
      onSubmit={handleSubmit}
      showConfirmation={true}
    />
  );
};

// Example 5: Full assignment submission flow with all features
export const FullSubmissionFlowExample: React.FC = () => {
  const mockAssignment: Assignment = {
    id: 5,
    title: 'Комплексное задание с несколькими типами вопросов',
    description: 'Задание включает тесты, открытые вопросы и загрузку файлов',
    instructions: `
      Структура задания:
      1. Часть А: Выберите один правильный ответ (5 вопросов × 2 балла)
      2. Часть Б: Выберите несколько ответов (3 вопроса × 4 балла)
      3. Часть В: Ответьте на открытые вопросы (2 вопроса × 8 баллов)
      4. Дополнительно: Загрузите поддерживающие материалы
    `,
    type: 'test',
    status: 'published',
    max_score: 50,
    time_limit: 90,
    attempts_limit: 2,
    start_date: new Date().toISOString(),
    due_date: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString(),
    tags: 'comprehensive,test,mixed',
    difficulty_level: 3,
    author: {
      id: 1,
      email: 'teacher@example.com',
      full_name: 'Иван Петров',
    },
    assigned_to: [1, 2, 3, 4, 5],
    is_overdue: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: any, files: File[]) => {
    setIsLoading(true);
    setError(null);

    try {
      // Validation
      if (!data.notes.trim() && files.length === 0) {
        throw new Error('Пожалуйста, заполните ответы или загрузите файл');
      }

      // API call
      const response = await fetch('/api/assignments/submit', {
        method: 'POST',
        body: JSON.stringify({
          assignment_id: mockAssignment.id,
          answers: data.answers,
          notes: data.notes,
          files: files.map((f) => f.name),
        }),
      });

      if (!response.ok) {
        throw new Error('Ошибка при отправке задания');
      }

      console.log('Submission successful');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-900">
          {error}
        </div>
      )}

      <AssignmentSubmitForm
        assignment={mockAssignment}
        questionCount={10} // 5 + 3 + 2
        onSubmit={handleSubmit}
        isLoading={isLoading}
        showConfirmation={true}
      />
    </div>
  );
};
