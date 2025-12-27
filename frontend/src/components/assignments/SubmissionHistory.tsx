import React from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Clock,
  CheckCircle,
  AlertCircle,
  Eye,
  Download,
} from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { ru } from 'date-fns/locale';

export interface SubmissionHistoryItem {
  id: number;
  attemptNumber: number;
  submittedAt: string;
  status: 'submitted' | 'graded' | 'returned';
  score?: number;
  maxScore?: number;
  feedback?: string;
  timeSpent?: number; // in seconds
  filesCount?: number;
  answersCount?: number;
}

export interface SubmissionHistoryProps {
  submissions: SubmissionHistoryItem[];
  isLoading?: boolean;
  onViewDetails?: (submissionId: number) => void;
  onDownloadFile?: (submissionId: number) => void;
}

export const SubmissionHistory: React.FC<SubmissionHistoryProps> = ({
  submissions,
  isLoading = false,
  onViewDetails,
  onDownloadFile,
}) => {
  const formatTimeSpent = (seconds?: number): string => {
    if (!seconds) return '-';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    const parts = [];
    if (hours > 0) parts.push(`${hours}ч`);
    if (minutes > 0) parts.push(`${minutes}м`);
    if (secs > 0) parts.push(`${secs}с`);

    return parts.length > 0 ? parts.join(' ') : '0с';
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'submitted':
        return <Badge variant="outline">Отправлено</Badge>;
      case 'graded':
        return (
          <Badge variant="default" className="bg-green-600">
            <CheckCircle className="w-3 h-3 mr-1" />
            Оценено
          </Badge>
        );
      case 'returned':
        return (
          <Badge variant="secondary">
            <AlertCircle className="w-3 h-3 mr-1" />
            Возвращено
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getScorePercentage = (score?: number, maxScore?: number) => {
    if (!score || !maxScore) return 0;
    return (score / maxScore) * 100;
  };

  const getScoreColor = (percentage: number) => {
    if (percentage >= 80) return 'bg-green-100';
    if (percentage >= 60) return 'bg-yellow-100';
    if (percentage >= 40) return 'bg-orange-100';
    return 'bg-red-100';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="w-5 h-5" />
          История отправок
        </CardTitle>
        <CardDescription>
          Всего отправлено: {submissions.length} попыток
        </CardDescription>
      </CardHeader>

      <CardContent>
        {submissions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>Вы еще не отправляли ответы на это задание</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Попытка</TableHead>
                  <TableHead>Дата и время</TableHead>
                  <TableHead>Статус</TableHead>
                  <TableHead className="text-right">Баллы</TableHead>
                  <TableHead className="text-right">Время</TableHead>
                  <TableHead>Файлы</TableHead>
                  <TableHead className="text-right">Действия</TableHead>
                </TableRow>
              </TableHeader>

              <TableBody>
                {submissions.map((submission, index) => {
                  const scorePercentage = getScorePercentage(
                    submission.score,
                    submission.maxScore
                  );

                  return (
                    <TableRow key={submission.id} className="hover:bg-muted/50">
                      <TableCell className="font-medium">
                        #{submission.attemptNumber}
                      </TableCell>

                      <TableCell>
                        <div className="space-y-1">
                          <p className="font-medium">
                            {format(new Date(submission.submittedAt), 'PPp', {
                              locale: ru,
                            })}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {formatDistanceToNow(new Date(submission.submittedAt), {
                              addSuffix: true,
                              locale: ru,
                            })}
                          </p>
                        </div>
                      </TableCell>

                      <TableCell>
                        {getStatusBadge(submission.status)}
                      </TableCell>

                      <TableCell className="text-right">
                        {submission.score !== undefined && submission.maxScore ? (
                          <div className="space-y-2">
                            <div className="text-sm font-medium">
                              {submission.score} / {submission.maxScore}
                            </div>
                            <Progress
                              value={scorePercentage}
                              className="w-24 h-2"
                            />
                            <div className={`text-xs font-medium px-2 py-1 rounded w-fit ${getScoreColor(scorePercentage)}`}>
                              {Math.round(scorePercentage)}%
                            </div>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>

                      <TableCell className="text-right">
                        {formatTimeSpent(submission.timeSpent)}
                      </TableCell>

                      <TableCell>
                        <Badge variant="outline">
                          {submission.filesCount || 0} файлов
                        </Badge>
                      </TableCell>

                      <TableCell className="text-right space-x-2">
                        {onViewDetails && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onViewDetails(submission.id)}
                            title="Посмотреть детали"
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                        )}
                        {onDownloadFile && submission.filesCount && submission.filesCount > 0 && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onDownloadFile(submission.id)}
                            title="Скачать файлы"
                          >
                            <Download className="w-4 h-4" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}

        {/* Summary Stats */}
        {submissions.length > 0 && (
          <div className="mt-6 pt-6 border-t grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">Всего попыток</p>
              <p className="text-2xl font-bold">{submissions.length}</p>
            </div>

            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">Лучший результат</p>
              <p className="text-2xl font-bold">
                {submissions.length > 0
                  ? Math.max(...submissions
                    .filter((s) => s.score !== undefined)
                    .map((s) => ((s.score || 0) / (s.maxScore || 1)) * 100)
                  ).toFixed(0) + '%'
                  : '-'}
              </p>
            </div>

            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">Общее время</p>
              <p className="text-2xl font-bold">
                {formatTimeSpent(
                  submissions.reduce((sum, s) => sum + (s.timeSpent || 0), 0)
                )}
              </p>
            </div>

            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">Оценено</p>
              <p className="text-2xl font-bold">
                {submissions.filter((s) => s.status === 'graded').length}/
                {submissions.length}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
