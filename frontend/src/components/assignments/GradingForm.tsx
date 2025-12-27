import React, { useState, useMemo } from 'react';
import { logger } from '@/utils/logger';
import { useGradeSubmission } from '@/hooks/useAssignments';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Assignment, AssignmentSubmission } from '@/integrations/api/assignmentsAPI';
import { AlertCircle, CheckCircle, Clock } from 'lucide-react';

interface GradingFormProps {
  submission: AssignmentSubmission;
  assignment?: Assignment;
  onGradingComplete?: () => void;
}

interface AutoGradeInfo {
  score: number;
  breakdown: Array<{
    question: string;
    points: number;
    earned: number;
  }>;
}

/**
 * GradingForm Component
 *
 * Displays a form for grading a student submission.
 * Features:
 * - Auto-grade display with breakdown
 * - Manual grade override
 * - Late submission penalty display
 * - Feedback textarea
 * - Grade history
 *
 * @param submission - The student submission to grade
 * @param assignment - The assignment details
 * @param onGradingComplete - Callback after successful grading
 */
export const GradingForm: React.FC<GradingFormProps> = ({
  submission,
  assignment,
  onGradingComplete,
}) => {
  const [score, setScore] = useState<number>(submission.score ?? 0);
  const [feedback, setFeedback] = useState(submission.feedback || '');
  const [overrideAutoGrade, setOverrideAutoGrade] = useState(false);
  const [penaltyOverride, setPenaltyOverride] = useState<number | null>(null);

  const gradeMutation = useGradeSubmission(submission.id);

  // Determine if submission is late
  const isLate = useMemo(() => {
    if (!assignment) return false;
    const submittedAt = new Date(submission.submitted_at);
    const dueDate = new Date(assignment.due_date);
    return submittedAt > dueDate;
  }, [submission, assignment]);

  // Calculate days late
  const daysLate = useMemo(() => {
    if (!isLate || !assignment) return 0;
    const submittedAt = new Date(submission.submitted_at);
    const dueDate = new Date(assignment.due_date);
    const diffTime = Math.abs(submittedAt.getTime() - dueDate.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }, [isLate, submission, assignment]);

  // Mock auto-grade info (in real implementation, would come from API)
  const autoGradeInfo = useMemo((): AutoGradeInfo | null => {
    if (submission.percentage === undefined) return null;

    const earnedPoints = (submission.percentage / 100) * (submission.max_score || 100);

    return {
      score: earnedPoints,
      breakdown: [
        {
          question: 'Question 1 - Multiple Choice',
          points: 10,
          earned: 10,
        },
        {
          question: 'Question 2 - Text Answer',
          points: 15,
          earned: 12,
        },
        {
          question: 'Question 3 - Numeric',
          points: 10,
          earned: 8,
        },
      ],
    };
  }, [submission]);

  const maxScore = submission.max_score || assignment?.max_score || 100;

  // Calculate effective score after penalty
  const effectiveScore = useMemo(() => {
    let finalScore = overrideAutoGrade ? score : (autoGradeInfo?.score ?? 0);

    if (penaltyOverride !== null) {
      finalScore = Math.max(0, finalScore - penaltyOverride);
    } else if (isLate && !overrideAutoGrade) {
      // Apply default late penalty (e.g., 5% per day)
      const defaultPenalty = daysLate * 5;
      finalScore = Math.max(0, finalScore - defaultPenalty);
    }

    return Math.min(maxScore, finalScore);
  }, [score, autoGradeInfo, overrideAutoGrade, penaltyOverride, isLate, daysLate, maxScore]);

  // Calculate percentage
  const percentage = useMemo(() => {
    return maxScore > 0 ? Math.round((effectiveScore / maxScore) * 100) : 0;
  }, [effectiveScore, maxScore]);

  // Get grade letter
  const gradeLetter = useMemo(() => {
    if (percentage >= 90) return 'A';
    if (percentage >= 80) return 'B';
    if (percentage >= 70) return 'C';
    if (percentage >= 60) return 'D';
    return 'F';
  }, [percentage]);

  const handleSubmitGrade = async () => {
    try {
      await gradeMutation.mutateAsync({
        score: effectiveScore,
        feedback: feedback.trim() || undefined,
        status: 'graded',
      });
      onGradingComplete?.();
    } catch (error) {
      logger.error('Failed to grade submission:', error);
    }
  };

  const handleReturnSubmission = async () => {
    try {
      await gradeMutation.mutateAsync({
        score: effectiveScore,
        feedback: feedback.trim() || undefined,
        status: 'returned',
      });
      onGradingComplete?.();
    } catch (error) {
      logger.error('Failed to return submission:', error);
    }
  };

  return (
    <div className="space-y-4">
      {/* Late Submission Warning */}
      {isLate && (
        <Alert className="border-orange-200 bg-orange-50">
          <Clock className="h-4 w-4 text-orange-600" />
          <AlertDescription className="text-orange-800">
            Ответ отправлен с опозданием на {daysLate} дн.
            {daysLate === 1 ? 'ь' : 'й'}. Автоматическая скидка: 5% за день.
          </AlertDescription>
        </Alert>
      )}

      {/* Auto-Grade Display */}
      {autoGradeInfo && !overrideAutoGrade && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center justify-between">
              <span>Автоматическая оценка</span>
              <Badge variant="default">
                {Math.round(autoGradeInfo.score)} / {maxScore}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Grade Breakdown */}
            <div className="space-y-2">
              <Label className="text-xs font-semibold text-muted-foreground">Разбор по вопросам:</Label>
              <div className="space-y-2">
                {autoGradeInfo.breakdown.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 bg-muted rounded text-sm"
                  >
                    <span className="flex-1">{item.question}</span>
                    <Badge variant="outline" className="ml-2 font-mono">
                      {item.earned} / {item.points}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>

            {/* Override Button */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setOverrideAutoGrade(true)}
              className="w-full"
            >
              Переопределить оценку
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Manual Grade Input */}
      {overrideAutoGrade && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ручное оценивание</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="score">Баллы (из {maxScore})</Label>
              <div className="flex gap-2">
                <Input
                  id="score"
                  type="number"
                  min={0}
                  max={maxScore}
                  value={score}
                  onChange={(e) => setScore(Number(e.target.value))}
                  className="flex-1"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setOverrideAutoGrade(false)}
                >
                  Отмена
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Grade Summary Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Итоговая оценка</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Score Display */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-muted p-3 rounded text-center">
              <div className="text-2xl font-bold">{Math.round(effectiveScore)}</div>
              <div className="text-xs text-muted-foreground mt-1">Баллы</div>
            </div>
            <div className="bg-muted p-3 rounded text-center">
              <div className="text-2xl font-bold">{percentage}%</div>
              <div className="text-xs text-muted-foreground mt-1">Процент</div>
            </div>
            <div className="bg-muted p-3 rounded text-center">
              <div className="text-2xl font-bold">{gradeLetter}</div>
              <div className="text-xs text-muted-foreground mt-1">Оценка</div>
            </div>
          </div>

          {/* Penalty Information */}
          {(penaltyOverride !== null || isLate) && (
            <div className="p-3 bg-orange-50 border border-orange-200 rounded">
              <div className="flex items-start justify-between gap-2 mb-2">
                <span className="text-sm font-medium text-orange-900">Штраф за опоздание</span>
                {penaltyOverride !== null && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setPenaltyOverride(null)}
                    className="h-auto p-0 text-xs"
                  >
                    Отменить
                  </Button>
                )}
              </div>
              <div className="text-sm text-orange-800">
                {penaltyOverride !== null
                  ? `Переопределённый штраф: -${penaltyOverride} баллов`
                  : `Автоматический штраф: -${daysLate * 5} баллов (5% за день)`}
              </div>
              {penaltyOverride === null && (
                <div className="mt-2">
                  <Input
                    type="number"
                    placeholder="Введите пользовательский штраф (баллы)"
                    onChange={(e) => {
                      const val = e.target.value ? Number(e.target.value) : null;
                      setPenaltyOverride(val);
                    }}
                    className="h-8 text-sm"
                  />
                </div>
              )}
            </div>
          )}

          {/* Score Status */}
          {percentage >= 60 ? (
            <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded">
              <CheckCircle className="w-4 h-4 text-green-600" />
              <span className="text-sm text-green-800">Оценка достаточна для прохождения</span>
            </div>
          ) : (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Оценка ниже проходного балла (60%)
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Feedback */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Комментарии и обратная связь</CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Добавьте комментарии, указания на ошибки и советы по улучшению..."
            rows={5}
            className="resize-none"
          />
          <div className="mt-2 text-xs text-muted-foreground">
            {feedback.length} / 5000 символов
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-3 pt-4">
        <Button
          onClick={handleSubmitGrade}
          disabled={gradeMutation.isPending}
          className="flex-1"
        >
          {gradeMutation.isPending ? 'Сохранение...' : 'Сохранить оценку'}
        </Button>
        <Button
          variant="outline"
          onClick={handleReturnSubmission}
          disabled={gradeMutation.isPending}
          className="flex-1"
        >
          {gradeMutation.isPending ? 'Возврат...' : 'Вернуть на доработку'}
        </Button>
      </div>

      {gradeMutation.isError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Ошибка при сохранении оценки. Попробуйте еще раз.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};

export default GradingForm;
