import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  ScrollArea,
  ScrollBar,
} from '@/components/ui/scroll-area';
import { HelpCircle, MessageSquare, CheckCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface Question {
  id: number | string;
  text: string;
  type: 'single_choice' | 'multiple_choice' | 'text' | 'number' | 'essay';
  points: number;
  isRequired?: boolean;
}

export interface QuestionNavigatorProps {
  questions: Question[];
  currentQuestionId?: number | string;
  answeredQuestions?: (number | string)[];
  flaggedQuestions?: (number | string)[];
  timePerQuestion?: Record<number | string, number>; // in seconds
  onSelectQuestion: (questionId: number | string) => void;
  disabled?: boolean;
}

export const QuestionNavigator: React.FC<QuestionNavigatorProps> = ({
  questions,
  currentQuestionId,
  answeredQuestions = [],
  flaggedQuestions = [],
  timePerQuestion = {},
  onSelectQuestion,
  disabled = false,
}) => {
  const answered = useMemo(() => answeredQuestions.length, [answeredQuestions]);
  const total = useMemo(() => questions.length, [questions]);
  const progressPercentage = useMemo(() => (answered / total) * 100, [answered, total]);

  const getQuestionStatus = (questionId: number | string) => {
    const isAnswered = answeredQuestions.includes(questionId);
    const isFlagged = flaggedQuestions.includes(questionId);
    const isCurrent = questionId === currentQuestionId;

    return { isAnswered, isFlagged, isCurrent };
  };

  const getQuestionIcon = (questionId: number | string) => {
    const { isAnswered, isFlagged } = getQuestionStatus(questionId);

    if (isFlagged) {
      return <HelpCircle className="w-4 h-4 text-amber-500" />;
    }

    if (isAnswered) {
      return <CheckCircle className="w-4 h-4 text-green-600" />;
    }

    return <MessageSquare className="w-4 h-4 text-muted-foreground" />;
  };

  const totalPoints = useMemo(
    () => questions.reduce((sum, q) => sum + q.points, 0),
    [questions]
  );

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Навигация по вопросам</CardTitle>

        {/* Progress Bar */}
        <div className="mt-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="font-medium">Прогресс: {answered}/{total}</span>
            <span className="text-muted-foreground">
              {progressPercentage.toFixed(0)}%
            </span>
          </div>
          <Progress value={progressPercentage} className="h-2" />
        </div>

        {/* Stats */}
        <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Всего баллов</p>
            <p className="font-semibold">{totalPoints}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Отвечено</p>
            <p className="font-semibold">{answered}/{total}</p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden flex flex-col">
        <ScrollArea className="flex-1">
          <div className="pr-4 space-y-2">
            {questions.map((question, index) => {
              const { isAnswered, isFlagged, isCurrent } = getQuestionStatus(
                question.id
              );
              const timeSpent = timePerQuestion[question.id] || 0;

              return (
                <Button
                  key={question.id}
                  variant={isCurrent ? 'default' : 'outline'}
                  className={cn(
                    'w-full justify-start gap-3 h-auto py-3 px-3',
                    isCurrent && 'ring-2 ring-offset-2'
                  )}
                  onClick={() => onSelectQuestion(question.id)}
                  disabled={disabled}
                >
                  {/* Icon */}
                  <div className="flex-shrink-0">
                    {getQuestionIcon(question.id)}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0 text-left">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <p className="text-sm font-medium truncate">
                          Вопрос {index + 1}
                        </p>
                        <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                          {question.text}
                        </p>
                      </div>
                      <Badge variant="secondary" className="flex-shrink-0 text-xs">
                        {question.points}б
                      </Badge>
                    </div>

                    {/* Status Indicators */}
                    <div className="flex gap-1 mt-2 flex-wrap">
                      {question.isRequired && (
                        <Badge
                          variant="outline"
                          className="text-xs bg-red-50"
                        >
                          Обязательно
                        </Badge>
                      )}

                      {isAnswered && (
                        <Badge
                          variant="outline"
                          className="text-xs bg-green-50 text-green-700"
                        >
                          Отвечено
                        </Badge>
                      )}

                      {isFlagged && (
                        <Badge
                          variant="outline"
                          className="text-xs bg-amber-50 text-amber-700"
                        >
                          На проверку
                        </Badge>
                      )}

                      {timeSpent > 0 && (
                        <Badge
                          variant="outline"
                          className="text-xs flex items-center gap-1"
                        >
                          <Clock className="w-3 h-3" />
                          {timeSpent < 60
                            ? `${timeSpent}с`
                            : `${Math.floor(timeSpent / 60)}м`}
                        </Badge>
                      )}
                    </div>
                  </div>
                </Button>
              );
            })}
          </div>
          <ScrollBar />
        </ScrollArea>

        {/* Legend */}
        <div className="mt-4 pt-4 border-t space-y-2 text-xs">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-600" />
            <span className="text-muted-foreground">Отвечено</span>
          </div>
          <div className="flex items-center gap-2">
            <HelpCircle className="w-4 h-4 text-amber-500" />
            <span className="text-muted-foreground">На проверку</span>
          </div>
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-muted-foreground" />
            <span className="text-muted-foreground">Не отвечено</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
