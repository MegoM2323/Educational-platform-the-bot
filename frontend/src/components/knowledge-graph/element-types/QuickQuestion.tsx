import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, XCircle } from 'lucide-react';
import type { ElementTypeProps, QuickQuestionContent, QuickQuestionAnswer } from '@/types/knowledgeGraph';

export const QuickQuestion: React.FC<ElementTypeProps> = ({
  element,
  progress,
  onSubmit,
  isLoading = false,
  readOnly = false,
}) => {
  const content = element.content as QuickQuestionContent;
  const previousAnswer = progress?.answer as QuickQuestionAnswer | null;

  const [selectedChoice, setSelectedChoice] = useState<number | null>(
    previousAnswer?.choice !== undefined ? previousAnswer.choice : null
  );
  const [showFeedback, setShowFeedback] = useState(false);
  const [error, setError] = useState<string>('');

  const isCompleted = progress?.status === 'completed';
  const isDisabled = isLoading || isCompleted || readOnly;

  useEffect(() => {
    if (previousAnswer?.choice !== undefined) {
      setSelectedChoice(previousAnswer.choice);
      setShowFeedback(isCompleted);
    }
  }, [previousAnswer, isCompleted]);

  const handleSubmit = async () => {
    setError('');

    if (selectedChoice === null) {
      setError('Пожалуйста, выберите ответ');
      return;
    }

    try {
      await onSubmit({ choice: selectedChoice });
      setShowFeedback(true);
    } catch (err) {
      setError('Ошибка при отправке ответа. Попробуйте ещё раз.');
    }
  };

  const isCorrectAnswer = (choiceIndex: number): boolean => {
    return choiceIndex === content.correct_answer;
  };

  const wasSelectedCorrect = (): boolean => {
    return selectedChoice === content.correct_answer;
  };

  return (
    <div className="space-y-4">
      {/* Вопрос */}
      <div className="prose prose-sm max-w-none dark:prose-invert">
        <p className="text-lg font-medium text-foreground">{content.question}</p>
      </div>

      {/* Варианты ответа */}
      <RadioGroup
        value={selectedChoice !== null ? selectedChoice.toString() : undefined}
        onValueChange={(value) => setSelectedChoice(parseInt(value))}
        disabled={isDisabled}
        className="space-y-3"
      >
        {content.choices.map((choice, index) => {
          const isSelected = selectedChoice === index;
          const isCorrect = isCorrectAnswer(index);
          const showCorrectMark = showFeedback && isCorrect;
          const showWrongMark = showFeedback && isSelected && !isCorrect;

          return (
            <div
              key={index}
              className={`flex items-start space-x-3 p-4 border rounded-lg transition-colors ${
                isSelected ? 'bg-primary/5 border-primary' : 'hover:bg-muted/50'
              } ${showCorrectMark ? 'bg-green-50 dark:bg-green-950/30 border-green-500' : ''} ${
                showWrongMark ? 'bg-red-50 dark:bg-red-950/30 border-red-500' : ''
              }`}
            >
              <RadioGroupItem
                value={index.toString()}
                id={`choice-${index}`}
                disabled={isDisabled}
              />
              <Label
                htmlFor={`choice-${index}`}
                className="flex-1 cursor-pointer text-sm leading-relaxed"
              >
                {choice}
              </Label>

              {showCorrectMark && (
                <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
              )}
              {showWrongMark && (
                <XCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
              )}
            </div>
          );
        })}
      </RadioGroup>

      {/* Результат */}
      {showFeedback && isCompleted && (
        <div className="space-y-2">
          {wasSelectedCorrect() ? (
            <Alert className="bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-sm text-green-800 dark:text-green-200">
                Правильно! Вы выбрали верный ответ.
              </AlertDescription>
            </Alert>
          ) : (
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertDescription className="text-sm">
                Неправильно. Правильный ответ: {content.choices[content.correct_answer]}
              </AlertDescription>
            </Alert>
          )}

          {progress?.score !== null && (
            <div className="flex items-center gap-2">
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
      )}

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
          disabled={isDisabled || selectedChoice === null}
          className="w-full"
        >
          {isLoading ? 'Отправка...' : 'Проверить ответ'}
        </Button>
      )}
    </div>
  );
};
