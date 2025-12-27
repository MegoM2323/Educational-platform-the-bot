import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AssignmentSubmission } from '@/integrations/api/assignmentsAPI';
import { CheckCircle, XCircle, HelpCircle, FileText } from 'lucide-react';

interface SubmissionAnswerDisplayProps {
  submission: AssignmentSubmission;
}

interface Answer {
  questionNumber: number;
  questionText: string;
  questionType: string;
  studentAnswer: string;
  correctAnswer?: string;
  isCorrect?: boolean;
  pointsEarned?: number;
  maxPoints?: number;
}

/**
 * SubmissionAnswerDisplay Component
 *
 * Displays student answers in a readable format.
 * Features:
 * - Answer validation status (correct/incorrect/partial)
 * - Point allocation
 * - File attachments
 * - Answer highlighting
 *
 * @param submission - The submission to display
 */
export const SubmissionAnswerDisplay: React.FC<SubmissionAnswerDisplayProps> = ({
  submission,
}) => {
  const [expandedAnswer, setExpandedAnswer] = useState<number | null>(null);

  // Mock answers data (in real implementation, would come from API)
  const answers = useMemo((): Answer[] => {
    return [
      {
        questionNumber: 1,
        questionText: 'Вопрос 1: Что такое переменная в программировании?',
        questionType: 'multiple_choice',
        studentAnswer: 'Именованное место в памяти для хранения данных',
        correctAnswer: 'Именованное место в памяти для хранения данных',
        isCorrect: true,
        pointsEarned: 10,
        maxPoints: 10,
      },
      {
        questionNumber: 2,
        questionText: 'Вопрос 2: Дайте определение класса в объектно-ориентированном программировании',
        questionType: 'text',
        studentAnswer: 'Класс - это шаблон для создания объектов с определёнными свойствами и методами',
        isCorrect: true,
        pointsEarned: 8,
        maxPoints: 10,
      },
      {
        questionNumber: 3,
        questionText: 'Вопрос 3: Найдите сумму 5 + 3 * 2',
        questionType: 'number',
        studentAnswer: '16',
        correctAnswer: '11',
        isCorrect: false,
        pointsEarned: 0,
        maxPoints: 10,
      },
      {
        questionNumber: 4,
        questionText: 'Вопрос 4: Выберите все верные утверждения о функциях',
        questionType: 'multiple_choice',
        studentAnswer: 'Функции могут возвращать значения; Функции могут принимать параметры',
        correctAnswer: 'Функции могут возвращать значения; Функции могут принимать параметры; Функции могут быть вложенными',
        isCorrect: false,
        pointsEarned: 6,
        maxPoints: 10,
      },
    ];
  }, []);

  // Calculate answer statistics
  const stats = useMemo(() => {
    const correct = answers.filter(a => a.isCorrect).length;
    const incorrect = answers.filter(a => a.isCorrect === false).length;
    const total = answers.length;
    return {
      correct,
      incorrect,
      total,
      correctPercentage: Math.round((correct / total) * 100),
    };
  }, [answers]);

  const getAnswerIcon = (isCorrect?: boolean) => {
    if (isCorrect === true) {
      return <CheckCircle className="w-5 h-5 text-green-600" />;
    } else if (isCorrect === false) {
      return <XCircle className="w-5 h-5 text-red-600" />;
    }
    return <HelpCircle className="w-5 h-5 text-gray-400" />;
  };

  const getQuestionTypeLabel = (type: string): string => {
    switch (type) {
      case 'single_choice':
        return 'Один ответ';
      case 'multiple_choice':
        return 'Несколько ответов';
      case 'text':
        return 'Текстовый ответ';
      case 'number':
        return 'Числовой ответ';
      default:
        return type;
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Ответы студента</CardTitle>
          <div className="flex gap-2">
            <Badge variant="outline">
              Всего: {stats.total}
            </Badge>
            <Badge variant="default">
              Верно: {stats.correct}
            </Badge>
            <Badge variant="destructive">
              Ошибок: {stats.incorrect}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {submission.file ? (
          <Tabs defaultValue="content" className="w-full">
            <TabsList>
              <TabsTrigger value="content">Содержание</TabsTrigger>
              <TabsTrigger value="file">Приложение</TabsTrigger>
            </TabsList>

            {/* Content Tab */}
            <TabsContent value="content" className="space-y-3 mt-4">
              {submission.content && (
                <div className="p-3 bg-muted rounded text-sm whitespace-pre-wrap">
                  {submission.content}
                </div>
              )}

              {answers.length > 0 && (
                <div className="space-y-2 mt-4">
                  <h4 className="font-medium text-sm mb-3">Структурированные ответы:</h4>
                  <ScrollArea className="h-96 pr-4">
                    <div className="space-y-2">
                      {answers.map(answer => (
                        <div
                          key={answer.questionNumber}
                          className={`p-3 rounded border transition-colors cursor-pointer hover:bg-muted ${
                            expandedAnswer === answer.questionNumber
                              ? 'bg-muted border-primary'
                              : 'bg-background'
                          }`}
                          onClick={() =>
                            setExpandedAnswer(
                              expandedAnswer === answer.questionNumber
                                ? null
                                : answer.questionNumber
                            )
                          }
                        >
                          <div className="flex items-start gap-3">
                            <div className="mt-0.5">
                              {getAnswerIcon(answer.isCorrect)}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-sm mb-1">
                                Вопрос {answer.questionNumber}
                              </div>
                              <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                                {answer.questionText}
                              </p>
                              <div className="flex items-center justify-between gap-2">
                                <Badge variant="secondary" className="text-xs">
                                  {getQuestionTypeLabel(answer.questionType)}
                                </Badge>
                                {answer.pointsEarned !== undefined && answer.maxPoints && (
                                  <Badge
                                    variant={
                                      answer.isCorrect ? 'default' : 'destructive'
                                    }
                                    className="text-xs font-mono"
                                  >
                                    {answer.pointsEarned} / {answer.maxPoints}
                                  </Badge>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Expanded View */}
                          {expandedAnswer === answer.questionNumber && (
                            <div className="mt-3 pt-3 border-t space-y-2">
                              <div>
                                <h5 className="text-xs font-semibold text-muted-foreground mb-1">
                                  Ответ студента:
                                </h5>
                                <p className="text-sm p-2 bg-muted rounded">
                                  {answer.studentAnswer}
                                </p>
                              </div>

                              {answer.correctAnswer && answer.isCorrect === false && (
                                <div>
                                  <h5 className="text-xs font-semibold text-green-600 mb-1">
                                    Правильный ответ:
                                  </h5>
                                  <p className="text-sm p-2 bg-green-50 rounded">
                                    {answer.correctAnswer}
                                  </p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>
              )}
            </TabsContent>

            {/* File Tab */}
            <TabsContent value="file" className="mt-4">
              <div className="p-4 border rounded bg-muted/30">
                <div className="flex items-start gap-3">
                  <FileText className="w-5 h-5 text-muted-foreground mt-0.5" />
                  <div className="flex-1">
                    <div className="font-medium text-sm mb-1">Приложенный файл</div>
                    <p className="text-xs text-muted-foreground mb-3">
                      {submission.file?.split('/').pop() || 'файл'}
                    </p>
                    <a
                      href={submission.file}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline"
                    >
                      Скачать файл
                    </a>
                  </div>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        ) : (
          <ScrollArea className="h-96 pr-4">
            {answers.length > 0 ? (
              <div className="space-y-2">
                {answers.map(answer => (
                  <div
                    key={answer.questionNumber}
                    className={`p-3 rounded border transition-colors cursor-pointer hover:bg-muted ${
                      expandedAnswer === answer.questionNumber
                        ? 'bg-muted border-primary'
                        : 'bg-background'
                    }`}
                    onClick={() =>
                      setExpandedAnswer(
                        expandedAnswer === answer.questionNumber
                          ? null
                          : answer.questionNumber
                      )
                    }
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5">
                        {getAnswerIcon(answer.isCorrect)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm mb-1">
                          Вопрос {answer.questionNumber}
                        </div>
                        <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                          {answer.questionText}
                        </p>
                        <div className="flex items-center justify-between gap-2">
                          <Badge variant="secondary" className="text-xs">
                            {getQuestionTypeLabel(answer.questionType)}
                          </Badge>
                          {answer.pointsEarned !== undefined && answer.maxPoints && (
                            <Badge
                              variant={answer.isCorrect ? 'default' : 'destructive'}
                              className="text-xs font-mono"
                            >
                              {answer.pointsEarned} / {answer.maxPoints}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Expanded View */}
                    {expandedAnswer === answer.questionNumber && (
                      <div className="mt-3 pt-3 border-t space-y-2">
                        <div>
                          <h5 className="text-xs font-semibold text-muted-foreground mb-1">
                            Ответ студента:
                          </h5>
                          <p className="text-sm p-2 bg-muted rounded">
                            {answer.studentAnswer}
                          </p>
                        </div>

                        {answer.correctAnswer && answer.isCorrect === false && (
                          <div>
                            <h5 className="text-xs font-semibold text-green-600 mb-1">
                              Правильный ответ:
                            </h5>
                            <p className="text-sm p-2 bg-green-50 rounded">
                              {answer.correctAnswer}
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 text-center">
                {submission.content ? (
                  <>
                    <p className="text-sm text-muted-foreground mb-3">Текстовое содержание:</p>
                    <p className="text-sm p-3 bg-muted rounded whitespace-pre-wrap">
                      {submission.content}
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Нет структурированных ответов для отображения
                  </p>
                )}
              </div>
            )}
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
};

export default SubmissionAnswerDisplay;
