/**
 * Пример использования ElementCard компонента
 *
 * НЕ ВКЛЮЧАТЬ В PRODUCTION BUILD - только для разработки
 */

import { useState } from 'react';
import { ElementCard } from './ElementCard';
import type { Element, ElementProgress, ElementAnswer } from '@/types/knowledgeGraph';

export const ElementCardExample = () => {
  const [isLoading, setIsLoading] = useState(false);

  // Пример 1: Текстовая задача
  const textProblemElement: Element = {
    id: '1',
    title: 'Решение квадратного уравнения',
    description: 'Решите квадратное уравнение методом дискриминанта',
    element_type: 'text_problem',
    element_type_display: 'Текстовая задача',
    content: {
      problem_text: 'Решите уравнение: x² - 5x + 6 = 0',
      hints: [
        'Используйте формулу дискриминанта: D = b² - 4ac',
        'Корни находятся по формуле: x = (-b ± √D) / 2a',
      ],
    },
    difficulty: 5,
    estimated_time_minutes: 15,
    max_score: 100,
    tags: ['математика', 'алгебра', 'квадратные уравнения'],
    is_public: true,
    created_by: {
      id: 1,
      name: 'Иван Иванов',
      email: 'teacher@example.com',
      role: 'teacher',
    },
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:00:00Z',
  };

  // Пример 2: Быстрый вопрос
  const quickQuestionElement: Element = {
    id: '2',
    title: 'Столица России',
    description: 'Выберите правильный ответ',
    element_type: 'quick_question',
    element_type_display: 'Быстрый вопрос',
    content: {
      question: 'Какой город является столицей России?',
      choices: ['Санкт-Петербург', 'Москва', 'Новосибирск', 'Казань'],
      correct_answer: 1,
    },
    difficulty: 2,
    estimated_time_minutes: 2,
    max_score: 50,
    tags: ['география', 'россия'],
    is_public: true,
    created_by: {
      id: 1,
      name: 'Иван Иванов',
      email: 'teacher@example.com',
      role: 'teacher',
    },
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:00:00Z',
  };

  // Пример 3: Теория
  const theoryElement: Element = {
    id: '3',
    title: 'Введение в Python',
    description: 'Основы синтаксиса языка программирования Python',
    element_type: 'theory',
    element_type_display: 'Теория',
    content: {
      text: `
        <h2>Python - язык программирования</h2>
        <p>Python - это высокоуровневый язык программирования общего назначения.</p>
        <h3>Основные особенности:</h3>
        <ul>
          <li>Простой и понятный синтаксис</li>
          <li>Динамическая типизация</li>
          <li>Большая стандартная библиотека</li>
        </ul>
        <pre><code>print("Hello, World!")</code></pre>
      `,
      sections: [
        {
          title: 'Переменные в Python',
          content: '<p>В Python переменные создаются автоматически при присваивании значения.</p><pre><code>x = 5\ny = "Hello"</code></pre>',
        },
        {
          title: 'Типы данных',
          content: '<p>Основные типы данных: int, float, str, bool, list, dict, tuple</p>',
        },
      ],
    },
    difficulty: 3,
    estimated_time_minutes: 20,
    max_score: 50,
    tags: ['программирование', 'python', 'основы'],
    is_public: true,
    created_by: {
      id: 1,
      name: 'Иван Иванов',
      email: 'teacher@example.com',
      role: 'teacher',
    },
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:00:00Z',
  };

  // Пример 4: Видео (YouTube)
  const videoElement: Element = {
    id: '4',
    title: 'Основы физики: Механика',
    description: 'Видеоурок о законах Ньютона',
    element_type: 'video',
    element_type_display: 'Видео',
    content: {
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
      title: 'Законы Ньютона',
      description: 'Подробный разбор трёх законов Ньютона с примерами',
      duration_seconds: 600,
    },
    difficulty: 4,
    estimated_time_minutes: 10,
    max_score: 50,
    tags: ['физика', 'механика', 'законы ньютона'],
    is_public: true,
    created_by: {
      id: 1,
      name: 'Иван Иванов',
      email: 'teacher@example.com',
      role: 'teacher',
    },
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:00:00Z',
  };

  const handleSubmit = async (answer: ElementAnswer) => {
    setIsLoading(true);
    console.log('Submitted answer:', answer);

    // Имитация API запроса
    await new Promise((resolve) => setTimeout(resolve, 1000));

    setIsLoading(false);
    alert('Ответ сохранён!');
  };

  const handleError = (error: Error) => {
    console.error('Error:', error);
    alert(`Ошибка: ${error.message}`);
  };

  return (
    <div className="container mx-auto p-8 space-y-8">
      <h1 className="text-3xl font-bold">Примеры ElementCard</h1>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">1. Текстовая задача</h2>
        <ElementCard
          element={textProblemElement}
          onSubmit={handleSubmit}
          onError={handleError}
          isLoading={isLoading}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">2. Быстрый вопрос</h2>
        <ElementCard
          element={quickQuestionElement}
          onSubmit={handleSubmit}
          onError={handleError}
          isLoading={isLoading}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">3. Теория</h2>
        <ElementCard
          element={theoryElement}
          onSubmit={handleSubmit}
          onError={handleError}
          isLoading={isLoading}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">4. Видео</h2>
        <ElementCard
          element={videoElement}
          onSubmit={handleSubmit}
          onError={handleError}
          isLoading={isLoading}
        />
      </section>
    </div>
  );
};
