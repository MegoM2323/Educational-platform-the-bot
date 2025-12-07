import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Lightbulb } from 'lucide-react';
import type { ElementTypeProps, TextProblemContent, TextProblemAnswer } from '@/types/knowledgeGraph';

export const TextProblem: React.FC<ElementTypeProps> = ({
  element,
  progress,
  onSubmit,
  isLoading = false,
  readOnly = false,
}) => {
  const content = element.content as TextProblemContent;
  const previousAnswer = progress?.answer as TextProblemAnswer | null;

  const [answer, setAnswer] = useState<string>(previousAnswer?.text || '');
  const [showHints, setShowHints] = useState(false);
  const [error, setError] = useState<string>('');

  const isCompleted = progress?.status === 'completed';
  const isDisabled = isLoading || isCompleted || readOnly;

  const characterCount = answer.length;
  const maxCharacters = 5000;

  useEffect(() => {
    if (previousAnswer?.text) {
      setAnswer(previousAnswer.text);
    }
  }, [previousAnswer]);

  const handleSubmit = async () => {
    setError('');

    if (!answer.trim()) {
      setError('Пожалуйста, введите ответ');
      return;
    }

    if (answer.length > maxCharacters) {
      setError(`Ответ слишком длинный (максимум ${maxCharacters} символов)`);
      return;
    }

    try {
      await onSubmit({ text: answer.trim() });
    } catch (err) {
      setError('Ошибка при отправке ответа. Попробуйте ещё раз.');
    }
  };

  return (
    <div className="space-y-4">
      {/* Текст задачи */}
      <div className="prose prose-sm max-w-none dark:prose-invert">
        <div
          className="text-foreground whitespace-pre-wrap"
          dangerouslySetInnerHTML={{ __html: content.problem_text }}
        />
      </div>

      {/* Подсказки (опционально) */}
      {content.hints && content.hints.length > 0 && (
        <div className="space-y-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowHints(!showHints)}
            className="flex items-center gap-2"
          >
            <Lightbulb className="h-4 w-4" />
            {showHints ? 'Скрыть подсказки' : 'Показать подсказки'}
          </Button>

          {showHints && (
            <div className="space-y-2">
              {content.hints.map((hint, index) => (
                <Alert key={index} className="bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900">
                  <AlertDescription className="text-sm">
                    <strong>Подсказка {index + 1}:</strong> {hint}
                  </AlertDescription>
                </Alert>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Поле для ответа */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="answer" className="text-sm font-medium">
            Ваш ответ {!isCompleted && '*'}
          </Label>
          <span className="text-xs text-muted-foreground">
            {characterCount} / {maxCharacters}
          </span>
        </div>

        <Textarea
          id="answer"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Введите ваш ответ здесь..."
          rows={8}
          maxLength={maxCharacters}
          disabled={isDisabled}
          className="resize-none font-mono text-sm"
        />

        {isCompleted && progress?.score !== null && (
          <div className="flex items-center gap-2 mt-2">
            <Badge variant={progress.score >= element.max_score * 0.7 ? 'default' : 'secondary'}>
              Оценка: {progress.score} / {element.max_score}
            </Badge>
            {progress.score_percent !== undefined && (
              <span className="text-sm text-muted-foreground">
                ({progress.score_percent}%)
              </span>
            )}
          </div>
        )}
      </div>

      {/* Ошибки */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Кнопка отправки */}
      {!isCompleted && !readOnly && (
        <Button
          type="button"
          onClick={handleSubmit}
          disabled={isDisabled || !answer.trim()}
          className="w-full"
        >
          {isLoading ? 'Отправка...' : 'Отправить ответ'}
        </Button>
      )}

      {isCompleted && (
        <Alert className="bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900">
          <AlertDescription className="text-sm text-green-800 dark:text-green-200">
            Задача выполнена! Ответ сохранён.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};
