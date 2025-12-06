import { useEffect, useState } from 'react';
import { logger } from '@/utils/logger';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Loader2 } from 'lucide-react';
import { unifiedAPI } from '@/integrations/api/unifiedClient';

export interface Subject {
  id: number;
  name: string;
  description?: string;
  color?: string;
  is_active: boolean;
  assigned_at?: string;
}

interface SubjectMultiSelectProps {
  value: number[];
  onChange: (value: number[]) => void;
  disabled?: boolean;
}

export const SubjectMultiSelect = ({ value, onChange, disabled }: SubjectMultiSelectProps) => {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSubjects = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await unifiedAPI.request<{ success: boolean; count: number; results: Subject[] }>('/materials/subjects/all/', {
          method: 'GET',
        });

        if (!res.success) {
          throw new Error(res.error || 'Ошибка загрузки предметов');
        }

        // Backend returns {success: true, count: 5, results: [...]}
        // Extract the results array
        const data = res.data as any;
        const subjectsArray = Array.isArray(data) ? data : (data.results || []);
        setSubjects(subjectsArray);
      } catch (err: any) {
        logger.error('Error loading subjects:', err);
        setError(err.message || 'Не удалось загрузить список предметов');
      } finally {
        setLoading(false);
      }
    };

    loadSubjects();
  }, []);

  const handleToggle = (subjectId: number, checked: boolean) => {
    if (checked) {
      onChange([...value, subjectId]);
    } else {
      onChange(value.filter(id => id !== subjectId));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Загрузка предметов...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-sm text-destructive border border-destructive rounded-md">
        {error}
      </div>
    );
  }

  if (subjects.length === 0) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Предметы не найдены
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">
          Выберите предметы
        </Label>
        <span className="text-xs text-muted-foreground">
          Выбрано: {value.length} из {subjects.length}
        </span>
      </div>

      {/* Отображение выбранных предметов */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1 p-2 bg-muted rounded-md">
          {value.map(id => {
            const subject = subjects.find(s => s.id === id);
            return subject ? (
              <Badge key={id} variant="secondary">
                {subject.name}
              </Badge>
            ) : null;
          })}
        </div>
      )}

      {/* Список чекбоксов */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[400px] overflow-y-auto p-2 border rounded-md">
        {subjects.map(subject => (
          <div key={subject.id} className="flex items-center space-x-2">
            <Checkbox
              id={`subject-${subject.id}`}
              checked={value.includes(subject.id)}
              onCheckedChange={(checked) => handleToggle(subject.id, checked === true)}
              disabled={disabled}
            />
            <Label
              htmlFor={`subject-${subject.id}`}
              className={`text-sm cursor-pointer ${disabled ? 'opacity-50' : ''}`}
            >
              {subject.name}
              {subject.description && (
                <span className="block text-xs text-muted-foreground mt-0.5">
                  {subject.description}
                </span>
              )}
            </Label>
          </div>
        ))}
      </div>
    </div>
  );
};
