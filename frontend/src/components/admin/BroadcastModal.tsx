import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { adminAPI } from '@/integrations/api/adminAPI';
import { Input } from '@/components/ui/input';

interface BroadcastModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

type TargetGroup = 'all_students' | 'all_teachers' | 'all_tutors' | 'all_parents' | 'by_subject' | 'by_tutor' | 'custom';

interface PreviewRecipient {
  id: number;
  full_name: string;
  email: string;
  role: string;
}

export const BroadcastModal = ({ open, onOpenChange, onSuccess }: BroadcastModalProps) => {
  const [targetGroup, setTargetGroup] = useState<TargetGroup>('all_students');
  const [message, setMessage] = useState('');
  const [subjectId, setSubjectId] = useState<string>('');
  const [tutorId, setTutorId] = useState<string>('');
  const [customUserIds, setCustomUserIds] = useState('');
  const [loading, setLoading] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [preview, setPreview] = useState<{ count: number; recipients: PreviewRecipient[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Списки для выбора (заглушки - в реальности загрузить с бэкенда)
  const [subjects, setSubjects] = useState<Array<{ id: number; name: string }>>([]);
  const [tutors, setTutors] = useState<Array<{ id: number; user: { full_name: string } }>>([]);

  useEffect(() => {
    if (open) {
      // Загрузка списков для выбора
      loadFilterData();
    } else {
      // Сброс при закрытии
      resetForm();
    }
  }, [open]);

  const loadFilterData = async () => {
    try {
      // Загрузка фильтров из существующего API
      const [scheduleFilters, tutorsResponse] = await Promise.all([
        adminAPI.getScheduleFilters(),
        adminAPI.getTutors(),
      ]);

      if (scheduleFilters.success && scheduleFilters.data?.subjects) {
        setSubjects(scheduleFilters.data.subjects);
      }

      if (tutorsResponse.success && tutorsResponse.data) {
        const tutorsArray = Array.isArray(tutorsResponse.data)
          ? tutorsResponse.data
          : (tutorsResponse.data as any).results || [];
        setTutors(tutorsArray);
      }
    } catch (err) {
      console.error('Error loading filter data:', err);
    }
  };

  const resetForm = () => {
    setTargetGroup('all_students');
    setMessage('');
    setSubjectId('');
    setTutorId('');
    setCustomUserIds('');
    setPreview(null);
    setError(null);
  };

  const handlePreview = async () => {
    setError(null);
    setPreviewing(true);

    try {
      const data: any = {
        target_group: targetGroup,
      };

      if (targetGroup === 'by_subject' && subjectId) {
        data.subject_id = parseInt(subjectId);
      } else if (targetGroup === 'by_tutor' && tutorId) {
        data.tutor_id = parseInt(tutorId);
      } else if (targetGroup === 'custom' && customUserIds) {
        const ids = customUserIds.split(',').map((id) => parseInt(id.trim())).filter((id) => !isNaN(id));
        if (ids.length === 0) {
          setError('Введите корректные ID пользователей через запятую');
          return;
        }
        data.user_ids = ids;
      }

      const response = await adminAPI.previewBroadcast(data);

      if (response.success && response.data) {
        setPreview({
          count: response.data.recipients_count,
          recipients: response.data.recipients_preview || [],
        });
      } else {
        setError(response.error || 'Не удалось получить предпросмотр');
      }
    } catch (err: any) {
      setError(err?.message || 'Ошибка предпросмотра');
    } finally {
      setPreviewing(false);
    }
  };

  const handleSubmit = async () => {
    setError(null);

    if (!message.trim()) {
      setError('Введите текст сообщения');
      return;
    }

    if (message.length > 500) {
      setError('Текст сообщения не должен превышать 500 символов');
      return;
    }

    if (targetGroup === 'by_subject' && !subjectId) {
      setError('Выберите предмет');
      return;
    }

    if (targetGroup === 'by_tutor' && !tutorId) {
      setError('Выберите тьютора');
      return;
    }

    if (targetGroup === 'custom' && !customUserIds) {
      setError('Введите ID пользователей');
      return;
    }

    setLoading(true);

    try {
      const data: any = {
        target_group: targetGroup,
        message: message.trim(),
      };

      if (targetGroup === 'by_subject' && subjectId) {
        data.subject_id = parseInt(subjectId);
      } else if (targetGroup === 'by_tutor' && tutorId) {
        data.tutor_id = parseInt(tutorId);
      } else if (targetGroup === 'custom' && customUserIds) {
        const ids = customUserIds.split(',').map((id) => parseInt(id.trim())).filter((id) => !isNaN(id));
        data.user_ids = ids;
      }

      const response = await adminAPI.createBroadcast(data);

      if (response.success) {
        toast.success('Рассылка успешно отправлена');
        onSuccess();
        onOpenChange(false);
      } else {
        setError(response.error || 'Не удалось отправить рассылку');
      }
    } catch (err: any) {
      setError(err?.message || 'Ошибка отправки рассылки');
    } finally {
      setLoading(false);
    }
  };

  const getTargetGroupLabel = (group: TargetGroup): string => {
    switch (group) {
      case 'all_students':
        return 'Все студенты';
      case 'all_teachers':
        return 'Все учителя';
      case 'all_tutors':
        return 'Все тьютеры';
      case 'all_parents':
        return 'Все родители';
      case 'by_subject':
        return 'По предмету';
      case 'by_tutor':
        return 'По тьютору';
      case 'custom':
        return 'Кастомная группа';
      default:
        return '';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Создать рассылку</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Целевая группа */}
          <div className="space-y-2">
            <Label htmlFor="target-group">Целевая группа</Label>
            <Select value={targetGroup} onValueChange={(value) => setTargetGroup(value as TargetGroup)}>
              <SelectTrigger id="target-group">
                <SelectValue placeholder="Выберите группу" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all_students">Все студенты</SelectItem>
                <SelectItem value="all_teachers">Все учителя</SelectItem>
                <SelectItem value="all_tutors">Все тьютеры</SelectItem>
                <SelectItem value="all_parents">Все родители</SelectItem>
                <SelectItem value="by_subject">По предмету</SelectItem>
                <SelectItem value="by_tutor">По тьютору</SelectItem>
                <SelectItem value="custom">Кастомная группа (ID)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Предмет (если выбрано "По предмету") */}
          {targetGroup === 'by_subject' && (
            <div className="space-y-2">
              <Label htmlFor="subject">Предмет</Label>
              <Select value={subjectId} onValueChange={setSubjectId}>
                <SelectTrigger id="subject">
                  <SelectValue placeholder="Выберите предмет" />
                </SelectTrigger>
                <SelectContent>
                  {subjects.map((subject) => (
                    <SelectItem key={subject.id} value={subject.id.toString()}>
                      {subject.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Тьютор (если выбрано "По тьютору") */}
          {targetGroup === 'by_tutor' && (
            <div className="space-y-2">
              <Label htmlFor="tutor">Тьютор</Label>
              <Select value={tutorId} onValueChange={setTutorId}>
                <SelectTrigger id="tutor">
                  <SelectValue placeholder="Выберите тьютора" />
                </SelectTrigger>
                <SelectContent>
                  {tutors.map((tutor) => (
                    <SelectItem key={tutor.id} value={tutor.id.toString()}>
                      {tutor.user.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Кастомная группа (если выбрано "Кастомная группа") */}
          {targetGroup === 'custom' && (
            <div className="space-y-2">
              <Label htmlFor="custom-ids">ID пользователей (через запятую)</Label>
              <Input
                id="custom-ids"
                placeholder="1, 5, 10, 15"
                value={customUserIds}
                onChange={(e) => setCustomUserIds(e.target.value)}
              />
            </div>
          )}

          {/* Текст сообщения */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="message">Текст сообщения</Label>
              <span className={`text-sm ${message.length > 500 ? 'text-red-500' : 'text-muted-foreground'}`}>
                {message.length}/500
              </span>
            </div>
            <Textarea
              id="message"
              placeholder="Введите текст сообщения для рассылки..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={6}
              maxLength={500}
            />
          </div>

          {/* Предпросмотр */}
          {preview && (
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-2">
                  <p className="font-medium">Получателей: {preview.count}</p>
                  {preview.recipients.length > 0 && (
                    <div className="text-sm">
                      <p className="text-muted-foreground mb-1">Первые получатели:</p>
                      <ul className="space-y-1">
                        {preview.recipients.slice(0, 5).map((recipient) => (
                          <li key={recipient.id} className="text-xs">
                            {recipient.full_name} ({recipient.email}) - {recipient.role}
                          </li>
                        ))}
                        {preview.recipients.length > 5 && (
                          <li className="text-xs text-muted-foreground">...и еще {preview.recipients.length - 5}</li>
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Ошибка */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Отмена
          </Button>
          <Button type="button" variant="secondary" onClick={handlePreview} disabled={loading || previewing}>
            {previewing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Предпросмотр
          </Button>
          <Button type="button" onClick={handleSubmit} disabled={loading || !message.trim()}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Отправить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
