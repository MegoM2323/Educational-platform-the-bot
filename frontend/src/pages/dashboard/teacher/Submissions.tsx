import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { usePendingSubmissions, useProvideFeedback, useUpdateSubmissionStatus } from '@/hooks/useTeacher';
import { useState } from 'react';

export default function TeacherSubmissionsPage() {
  const { data: submissions, isLoading } = usePendingSubmissions();
  const provideFeedback = useProvideFeedback();
  const updateStatus = useUpdateSubmissionStatus();

  const [feedbackText, setFeedbackText] = useState<Record<number, string>>({});
  const [grade, setGrade] = useState<Record<number, string>>({});

  const submitFeedback = async (id: number) => {
    const text = feedbackText[id] || '';
    const g = grade[id] ? Number(grade[id]) : undefined;
    await provideFeedback.mutateAsync({ submissionId: id, data: { feedback_text: text, grade: g } });
    await updateStatus.mutateAsync({ submissionId: id, status: 'reviewed' });
  };

  return (
    <div className="p-6 space-y-6">
      <Card className="p-4">
        <h2 className="text-xl font-semibold mb-4">Задания на проверку</h2>
        {isLoading ? (
          <div>Загрузка...</div>
        ) : (
          <div className="space-y-4">
            {submissions?.map((s) => (
              <Card key={s.id} className="p-4 space-y-3">
                <div className="font-medium">{s.student_name}</div>
                <div className="text-sm text-muted-foreground">{s.material_title}</div>
                {s.submission_text && (
                  <div className="text-sm whitespace-pre-wrap">{s.submission_text}</div>
                )}
                {s.submission_file && (
                  <Button variant="outline" onClick={() => window.open(s.submission_file!, '_blank')}>Открыть файл</Button>
                )}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
                  <div className="md:col-span-3">
                    <Label>Фидбэк</Label>
                    <Textarea value={feedbackText[s.id] || ''} onChange={(e) => setFeedbackText({ ...feedbackText, [s.id]: e.target.value })} />
                  </div>
                  <div>
                    <Label>Оценка</Label>
                    <Input type="number" min={1} max={100} value={grade[s.id] || ''} onChange={(e) => setGrade({ ...grade, [s.id]: e.target.value })} />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button onClick={() => submitFeedback(s.id)} disabled={provideFeedback.isPending || updateStatus.isPending}>Отправить фидбэк</Button>
                  <Button variant="outline" onClick={() => updateStatus.mutate({ submissionId: s.id, status: 'needs_changes' })} disabled={updateStatus.isPending}>Запросить доработку</Button>
                </div>
              </Card>
            ))}
            {(submissions?.length || 0) === 0 && (
              <div>Нет заданий на проверку</div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
