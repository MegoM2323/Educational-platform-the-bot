/**
 * ElementRenderer - отображает элемент урока в зависимости от типа
 * Поддерживает: theory, video, text_problem, quick_question
 */

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle2, XCircle, Lightbulb } from 'lucide-react';

interface ElementContent {
  // Theory
  text?: string;
  sections?: Array<{ title: string; content: string }>;

  // Video
  url?: string;
  title?: string;
  description?: string;
  duration_seconds?: number;

  // Text Problem
  problem_text?: string;
  hints?: string[];

  // Quick Question
  question?: string;
  choices?: string[];
  correct_answer?: number;
}

interface ElementProps {
  element: {
    id: string;
    title: string;
    element_type: 'text_problem' | 'quick_question' | 'theory' | 'video';
    content: ElementContent;
    max_score: number;
    estimated_time_minutes: number;
  };
  progress?: {
    status: 'not_started' | 'in_progress' | 'completed';
    score: number | null;
    answer: any | null;
  };
  onSubmit: (answer: any) => Promise<void>;
  onNext: () => void;
  isSubmitting: boolean;
  isLastElement: boolean;
}

export const ElementRenderer: React.FC<ElementProps> = ({
  element,
  progress,
  onSubmit,
  onNext,
  isSubmitting,
  isLastElement,
}) => {
  const [answer, setAnswer] = useState<any>(progress?.answer || null);
  const [showHint, setShowHint] = useState(false);
  const [submitResult, setSubmitResult] = useState<{
    success: boolean;
    is_correct?: boolean;
    score?: number;
    message?: string;
  } | null>(null);

  const handleSubmit = async () => {
    if (!answer) return;

    try {
      const result = await onSubmit(answer);
      // Для quick_question backend возвращает is_correct, score, can_retry
      // result может содержать { data: { is_correct, score, can_retry } }
      setSubmitResult({
        success: true,
        is_correct: (result as any)?.data?.is_correct,
        score: (result as any)?.data?.score,
        message: 'Ответ принят!',
      });
    } catch (error: any) {
      setSubmitResult({
        success: false,
        message: error.message || 'Ошибка отправки ответа',
      });
    }
  };

  const isCompleted = progress?.status === 'completed';

  // === THEORY ===
  if (element.element_type === 'theory') {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            📖 {element.title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {element.content.text && (
            <div className="prose prose-sm max-w-none">
              <p className="whitespace-pre-wrap">{element.content.text}</p>
            </div>
          )}

          {element.content.sections && element.content.sections.length > 0 && (
            <div className="space-y-4">
              {element.content.sections.map((section, idx) => (
                <div key={idx} className="border-l-4 border-blue-500 pl-4">
                  <h3 className="font-semibold text-lg mb-2">{section.title}</h3>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {section.content}
                  </p>
                </div>
              ))}
            </div>
          )}

          {isCompleted && (
            <Alert className="bg-green-50 border-green-200">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                ✓ Материал изучен
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
        <CardFooter className="flex justify-between">
          <div className="text-sm text-muted-foreground">
            ~{element.estimated_time_minutes} мин
          </div>
          {!isCompleted ? (
            <Button onClick={() => onSubmit({ viewed: true })} disabled={isSubmitting}>
              {isSubmitting ? 'Отправка...' : 'Отметить как прочитанное'}
            </Button>
          ) : (
            <Button onClick={onNext}>{isLastElement ? 'Завершить урок' : 'Дальше →'}</Button>
          )}
        </CardFooter>
      </Card>
    );
  }

  // === VIDEO ===
  if (element.element_type === 'video') {
    const videoUrl = element.content.url || '';
    const isYoutube = videoUrl.includes('youtube.com') || videoUrl.includes('youtu.be');

    // Получить YouTube embed URL
    const getYoutubeEmbedUrl = (url: string) => {
      const videoId = url.match(
        /(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\s]+)/
      )?.[1];
      return videoId ? `https://www.youtube.com/embed/${videoId}` : url;
    };

    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🎬 {element.title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {element.content.description && (
            <p className="text-sm text-muted-foreground">{element.content.description}</p>
          )}

          <div className="aspect-video w-full bg-black rounded-lg overflow-hidden">
            {isYoutube ? (
              <iframe
                width="100%"
                height="100%"
                src={getYoutubeEmbedUrl(videoUrl)}
                title={element.title}
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            ) : (
              <video controls className="w-full h-full">
                <source src={videoUrl} type="video/mp4" />
                Ваш браузер не поддерживает видео.
              </video>
            )}
          </div>

          {isCompleted && (
            <Alert className="bg-green-50 border-green-200">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                ✓ Видео просмотрено ({progress?.score || 0}/{element.max_score} баллов)
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
        <CardFooter className="flex justify-between">
          <div className="text-sm text-muted-foreground">
            {element.content.duration_seconds
              ? `${Math.floor(element.content.duration_seconds / 60)} мин`
              : `~${element.estimated_time_minutes} мин`}
          </div>
          {!isCompleted ? (
            <Button onClick={() => onSubmit({ watched_until: 100 })} disabled={isSubmitting}>
              {isSubmitting ? 'Отправка...' : 'Отметить как просмотренное'}
            </Button>
          ) : (
            <Button onClick={onNext}>{isLastElement ? 'Завершить урок' : 'Дальше →'}</Button>
          )}
        </CardFooter>
      </Card>
    );
  }

  // === TEXT PROBLEM ===
  if (element.element_type === 'text_problem') {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            ✏️ {element.title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="prose prose-sm max-w-none">
            <p className="whitespace-pre-wrap font-medium">
              {element.content.problem_text}
            </p>
          </div>

          {!isCompleted ? (
            <Textarea
              placeholder="Введите ваш ответ..."
              value={answer?.text || ''}
              onChange={(e) => setAnswer({ text: e.target.value })}
              disabled={isCompleted}
              rows={6}
              className="resize-none"
            />
          ) : (
            <div className="bg-muted p-4 rounded-lg">
              <p className="text-sm font-medium mb-1">Ваш ответ:</p>
              <p className="text-sm whitespace-pre-wrap">{answer?.text}</p>
            </div>
          )}

          {element.content.hints && element.content.hints.length > 0 && !isCompleted && (
            <div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowHint(!showHint)}
                className="text-blue-600"
              >
                <Lightbulb className="w-4 h-4 mr-2" />
                {showHint ? 'Скрыть подсказку' : 'Показать подсказку'}
              </Button>
              {showHint && (
                <Alert className="mt-2 bg-blue-50 border-blue-200">
                  <AlertDescription className="text-blue-800">
                    💡 {element.content.hints[0]}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}

          {submitResult && (
            <Alert
              className={
                submitResult.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
              }
            >
              {submitResult.success ? (
                <CheckCircle2 className="h-4 w-4 text-green-600" />
              ) : (
                <XCircle className="h-4 w-4 text-red-600" />
              )}
              <AlertDescription
                className={submitResult.success ? 'text-green-800' : 'text-red-800'}
              >
                {submitResult.message}
              </AlertDescription>
            </Alert>
          )}

          {isCompleted && (
            <Alert className="bg-yellow-50 border-yellow-200">
              <AlertDescription className="text-yellow-800">
                ⏳ Ожидает проверки преподавателем
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
        <CardFooter className="flex justify-between">
          <div className="text-sm text-muted-foreground">
            Макс. балл: {element.max_score}
          </div>
          {!isCompleted ? (
            <Button onClick={handleSubmit} disabled={isSubmitting || !answer?.text}>
              {isSubmitting ? 'Отправка...' : 'Отправить ответ'}
            </Button>
          ) : (
            <Button onClick={onNext}>{isLastElement ? 'Завершить урок' : 'Дальше →'}</Button>
          )}
        </CardFooter>
      </Card>
    );
  }

  // === QUICK QUESTION ===
  if (element.element_type === 'quick_question') {
    // Определяем правильность ответа: completed И score > 0
    const isCorrectAnswer = progress?.status === 'completed' && (progress?.score ?? 0) > 0;
    const isCorrect = submitResult?.is_correct;

    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            ❓ {element.title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="font-medium text-lg">{element.content.question}</p>

          <RadioGroup
            value={answer?.choice?.toString() || ''}
            onValueChange={(value) => {
              setAnswer({ choice: parseInt(value) });
              // Очищаем предыдущий результат при смене ответа (для чистого повторного запроса)
              setSubmitResult(null);
            }}
            disabled={isCorrectAnswer}
          >
            {element.content.choices?.map((choice, idx) => (
              <div key={idx} className="flex items-center space-x-2">
                <RadioGroupItem value={idx.toString()} id={`choice-${idx}`} />
                <Label htmlFor={`choice-${idx}`} className="cursor-pointer flex-1">
                  {choice}
                </Label>
              </div>
            ))}
          </RadioGroup>

          {submitResult && (
            <Alert
              className={
                isCorrect ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
              }
            >
              {isCorrect ? (
                <CheckCircle2 className="h-4 w-4 text-green-600" />
              ) : (
                <XCircle className="h-4 w-4 text-red-600" />
              )}
              <AlertDescription className={isCorrect ? 'text-green-800' : 'text-red-800'}>
                {isCorrect
                  ? `✓ Верно! Получено ${submitResult.score}/${element.max_score} баллов`
                  : '✗ Неверно. Попробуйте еще раз.'}
              </AlertDescription>
            </Alert>
          )}

          {isCorrectAnswer && !submitResult && (
            <Alert className="bg-green-50 border-green-200">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                ✓ Выполнено ({progress?.score || 0}/{element.max_score} баллов)
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
        <CardFooter className="flex justify-between">
          <div className="text-sm text-muted-foreground">
            Макс. балл: {element.max_score}
          </div>
          {!isCorrectAnswer ? (
            <Button onClick={handleSubmit} disabled={isSubmitting || answer?.choice === undefined}>
              {isSubmitting ? 'Отправка...' : 'Ответить'}
            </Button>
          ) : (
            <Button onClick={onNext}>{isLastElement ? 'Завершить урок' : 'Дальше →'}</Button>
          )}
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-muted-foreground">Неизвестный тип элемента: {element.element_type}</p>
      </CardContent>
    </Card>
  );
};
