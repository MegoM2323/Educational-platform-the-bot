import { useSubmissionFeedback } from '@/hooks/useStudent';
import { Card } from '@/components/ui/card';

interface Props {
  submissionId: number;
}

export default function FeedbackView({ submissionId }: Props) {
  const { data, isLoading } = useSubmissionFeedback(submissionId);

  if (isLoading) return <div>Загрузка фидбэка...</div>;
  if (!data) return null;

  return (
    <Card className="p-4 space-y-2">
      <div className="font-semibold">Фидбэк от преподавателя</div>
      <div className="text-sm whitespace-pre-wrap">{data.feedback_text}</div>
      {typeof data.grade !== 'undefined' && (
        <div className="text-sm">Оценка: {data.grade}</div>
      )}
      <div className="text-xs text-muted-foreground">{new Date(data.created_at).toLocaleString()}</div>
    </Card>
  );
}
