import { useEffect, useState } from 'react';
import { logger } from '@/utils/logger';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Loader2 } from 'lucide-react';
import { adminAPI } from '@/integrations/api/adminAPI';

export interface Student {
  id: number;
  user: {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
    is_active: boolean;
  };
  grade?: string;
}

interface StudentMultiSelectProps {
  value: number[];
  onChange: (value: number[]) => void;
  placeholder?: string;
  maxHeight?: number;
  disabled?: boolean;
}

export const StudentMultiSelect = ({
  value,
  onChange,
  placeholder = 'Выберите студентов...',
  maxHeight = 400,
  disabled
}: StudentMultiSelectProps) => {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadStudents = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await adminAPI.getStudents({ is_active: true, page_size: 1000 });

        if (!res.success) {
          throw new Error(res.error || 'Ошибка загрузки студентов');
        }

        const data = res.data;
        const studentsArray = data?.results || [];
        setStudents(studentsArray);
      } catch (err) {
        logger.error('Error loading students:', err);
        setError((err as Error).message || 'Не удалось загрузить список студентов');
      } finally {
        setLoading(false);
      }
    };

    loadStudents();
  }, []);

  const handleToggle = (studentId: number, checked: boolean) => {
    if (checked) {
      onChange([...value, studentId]);
    } else {
      onChange(value.filter(id => id !== studentId));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Загрузка студентов...</span>
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

  if (students.length === 0) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Студенты не найдены
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          {placeholder}
        </span>
        <span className="text-xs text-muted-foreground">
          Выбрано: {value.length} из {students.length}
        </span>
      </div>

      {value.length > 0 && (
        <div className="flex flex-wrap gap-1 p-2 bg-muted rounded-md">
          {value.map(id => {
            const student = students.find(s => s.id === id);
            return student ? (
              <Badge key={id} variant="secondary">
                {student.user.first_name} {student.user.last_name}
              </Badge>
            ) : null;
          })}
        </div>
      )}

      <div
        className="grid grid-cols-1 md:grid-cols-2 gap-3 overflow-y-auto p-2 border rounded-md"
        style={{ maxHeight: `${maxHeight}px` }}
      >
        {students.map(student => (
          <div key={student.id} className="flex items-center space-x-2">
            <Checkbox
              id={`student-${student.id}`}
              checked={value.includes(student.id)}
              onCheckedChange={(checked) => handleToggle(student.id, checked === true)}
              disabled={disabled}
            />
            <Label
              htmlFor={`student-${student.id}`}
              className={`text-sm cursor-pointer ${disabled ? 'opacity-50' : ''}`}
            >
              {student.user.first_name} {student.user.last_name}
              {student.grade && (
                <span className="block text-xs text-muted-foreground mt-0.5">
                  Класс: {student.grade}
                </span>
              )}
            </Label>
          </div>
        ))}
      </div>
    </div>
  );
};
