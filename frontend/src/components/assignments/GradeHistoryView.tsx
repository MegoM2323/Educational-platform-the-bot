import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { AssignmentSubmission } from '@/integrations/api/assignmentsAPI';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { CheckCircle, User } from 'lucide-react';

interface GradeHistoryViewProps {
  submission: AssignmentSubmission;
}

interface GradeHistory {
  id: number;
  date: string;
  grader: {
    name: string;
    email: string;
  };
  score: number;
  maxScore: number;
  feedback: string;
  status: 'graded' | 'returned' | 'appealed';
}

/**
 * GradeHistoryView Component
 *
 * Displays the grade history for a submission including:
 * - All previous grades
 * - Grader information
 * - Feedback history
 * - Status changes
 * - Score progression
 *
 * @param submission - The submission to view history for
 */
export const GradeHistoryView: React.FC<GradeHistoryViewProps> = ({
  submission,
}) => {
  // Mock grade history data (in real implementation, would come from API)
  const gradeHistory = useMemo((): GradeHistory[] => {
    const maxScore = submission.max_score || 100;

    // Include current grade if it exists
    const history: GradeHistory[] = [];

    if (submission.score !== undefined && submission.graded_at) {
      history.push({
        id: 1,
        date: submission.graded_at,
        grader: {
          name: 'Иван Петров',
          email: 'teacher@example.com',
        },
        score: submission.score,
        maxScore: maxScore,
        feedback:
          submission.feedback ||
          'Хорошая работа! Учите внимание к деталям в следующих заданиях.',
        status: submission.status as any,
      });
    }

    // Add mock previous grade if available
    if (submission.status === 'returned') {
      history.push({
        id: 2,
        date: new Date(new Date(submission.graded_at || new Date()).getTime() - 86400000).toISOString(),
        grader: {
          name: 'Мария Сидорова',
          email: 'assistant@example.com',
        },
        score: Math.max(0, (submission.score || 0) - 5),
        maxScore: maxScore,
        feedback: 'Требуется переделка. Обратите внимание на вторую часть задания.',
        status: 'returned',
      });
    }

    return history.sort(
      (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
    );
  }, [submission]);

  if (gradeHistory.length === 0) {
    return (
      <Card>
        <CardContent className="pt-12 pb-12 text-center">
          <CheckCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
          <h3 className="text-lg font-semibold mb-2">История оценок не найдена</h3>
          <p className="text-muted-foreground text-sm">
            Это задание еще не имеет оценок
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Grade Timeline */}
      <div className="space-y-3">
        {gradeHistory.map((entry, index) => (
          <Card key={entry.id}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1">
                  <Avatar className="w-10 h-10">
                    <AvatarFallback>
                      {entry.grader.name
                        .split(' ')
                        .map(n => n[0])
                        .join('')}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium">{entry.grader.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {entry.grader.email}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {format(new Date(entry.date), 'dd MMMM yyyy, HH:mm', {
                        locale: ru,
                      })}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <Badge variant="default" className="font-mono text-base mb-1">
                    {entry.score} / {entry.maxScore}
                  </Badge>
                  <Badge
                    variant={getStatusVariant(entry.status)}
                    className="text-xs block mt-1"
                  >
                    {getStatusLabel(entry.status)}
                  </Badge>
                </div>
              </div>
            </CardHeader>

            {entry.feedback && (
              <CardContent>
                <div className="bg-muted rounded p-3">
                  <p className="text-sm text-muted-foreground mb-1 font-medium">
                    Комментарий:
                  </p>
                  <p className="text-sm whitespace-pre-wrap">
                    {entry.feedback}
                  </p>
                </div>
              </CardContent>
            )}

            {/* Grade Metrics */}
            <CardContent className="pt-3">
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-muted rounded p-2 text-center">
                  <div className="text-xs text-muted-foreground">Процент</div>
                  <div className="text-lg font-bold mt-1">
                    {Math.round((entry.score / entry.maxScore) * 100)}%
                  </div>
                </div>
                <div className="bg-muted rounded p-2 text-center">
                  <div className="text-xs text-muted-foreground">Оценка</div>
                  <div className="text-lg font-bold mt-1">
                    {getGradeLetter(
                      Math.round((entry.score / entry.maxScore) * 100)
                    )}
                  </div>
                </div>
                <div className="bg-muted rounded p-2 text-center">
                  <div className="text-xs text-muted-foreground">Этап</div>
                  <div className="text-lg font-bold mt-1">
                    {index + 1} / {gradeHistory.length}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Statistics Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Итоги истории оценок</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-muted rounded">
              <div className="text-xs text-muted-foreground mb-1">
                Последняя оценка
              </div>
              <div className="text-2xl font-bold">
                {gradeHistory[0].score} / {gradeHistory[0].maxScore}
              </div>
            </div>
            <div className="p-3 bg-muted rounded">
              <div className="text-xs text-muted-foreground mb-1">
                Процент улучшения
              </div>
              <div className="text-2xl font-bold">
                {gradeHistory.length > 1
                  ? Math.round(
                      ((gradeHistory[0].score - gradeHistory[gradeHistory.length - 1].score) /
                        gradeHistory[gradeHistory.length - 1].score) *
                        100
                    )
                  : 0}
                %
              </div>
            </div>
            <div className="p-3 bg-muted rounded">
              <div className="text-xs text-muted-foreground mb-1">
                Всего попыток оценивания
              </div>
              <div className="text-2xl font-bold">{gradeHistory.length}</div>
            </div>
            <div className="p-3 bg-muted rounded">
              <div className="text-xs text-muted-foreground mb-1">
                Средняя оценка
              </div>
              <div className="text-2xl font-bold">
                {Math.round(
                  gradeHistory.reduce((sum, g) => sum + g.score, 0) /
                    gradeHistory.length
                )}
              </div>
            </div>
          </div>

          {/* Status Progression */}
          <div className="pt-3 border-t space-y-2">
            <h4 className="text-sm font-medium">Статусы:</h4>
            <div className="space-y-1">
              {gradeHistory.map((entry, idx) => (
                <div
                  key={entry.id}
                  className="flex items-center gap-2 text-sm"
                >
                  <div className="text-xs text-muted-foreground w-20">
                    {format(new Date(entry.date), 'dd.MM.yyyy', {
                      locale: ru,
                    })}
                  </div>
                  <Badge variant={getStatusVariant(entry.status)}>
                    {getStatusLabel(entry.status)}
                  </Badge>
                  <span className="text-muted-foreground">
                    {entry.score} / {entry.maxScore}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Feedback Trend */}
      {gradeHistory.some(g => g.feedback) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Все комментарии</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {gradeHistory
              .filter(g => g.feedback)
              .map(entry => (
                <div key={entry.id} className="pb-3 border-b last:border-b-0 last:pb-0">
                  <div className="flex items-start justify-between mb-2">
                    <div className="font-medium text-sm">{entry.grader.name}</div>
                    <span className="text-xs text-muted-foreground">
                      {format(new Date(entry.date), 'dd.MM.yyyy', {
                        locale: ru,
                      })}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {entry.feedback}
                  </p>
                </div>
              ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

// Helper functions
function getStatusVariant(
  status: string
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'graded':
      return 'default';
    case 'returned':
      return 'destructive';
    case 'appealed':
      return 'secondary';
    default:
      return 'outline';
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'graded':
      return 'Оценено';
    case 'returned':
      return 'Возвращено';
    case 'appealed':
      return 'Апелляция';
    default:
      return status;
  }
}

function getGradeLetter(percentage: number): string {
  if (percentage >= 90) return 'A';
  if (percentage >= 80) return 'B';
  if (percentage >= 70) return 'C';
  if (percentage >= 60) return 'D';
  return 'F';
}

export default GradeHistoryView;
