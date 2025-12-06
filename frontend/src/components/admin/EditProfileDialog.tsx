import { useState, useEffect } from 'react';
import { logger } from '@/utils/logger';
import { User } from '@/integrations/api/unifiedClient';
import {
  adminAPI,
  StudentProfileData,
  TeacherProfileData,
  TutorProfileData,
  ParentProfileData,
  Tutor,
  Parent,
} from '@/integrations/api/adminAPI';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { PrivateFieldTooltip } from './PrivateFieldTooltip';

interface EditProfileDialogProps {
  user: User;
  profile: any; // StudentProfile | TeacherProfile | TutorProfile | ParentProfile
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export const EditProfileDialog = ({ user, profile, open, onOpenChange, onSuccess }: EditProfileDialogProps) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tutors, setTutors] = useState<Tutor[]>([]);
  const [parents, setParents] = useState<Parent[]>([]);

  // Форма для студента
  const [studentForm, setStudentForm] = useState<StudentProfileData>({
    grade: profile?.grade || '',
    goal: profile?.goal || '',
    tutor_id: profile?.tutor?.id || null,
    parent_id: profile?.parent?.id || null,
  });

  // Форма для преподавателя
  const [teacherForm, setTeacherForm] = useState<TeacherProfileData>({
    experience_years: profile?.experience_years || 0,
    bio: profile?.bio || '',
  });

  // Форма для тьютора
  const [tutorForm, setTutorForm] = useState<TutorProfileData>({
    specialization: profile?.specialization || '',
    experience_years: profile?.experience_years || 0,
    bio: profile?.bio || '',
  });

  // Загрузка списков для селектов (студенты)
  useEffect(() => {
    if (user.role === 'student' && open) {
      loadSelectionData();
    }
  }, [user.role, open]);

  const loadSelectionData = async () => {
    try {
      const [tutorsResponse, parentsResponse] = await Promise.all([
        adminAPI.getTutors(),
        adminAPI.getParents(),
      ]);

      if (tutorsResponse.success && tutorsResponse.data) {
        // Backend returns { results: [...] }, extract the array
        const tutorsArray = Array.isArray(tutorsResponse.data)
          ? tutorsResponse.data
          : (tutorsResponse.data as any).results || [];
        setTutors(tutorsArray);
      }

      if (parentsResponse.success && parentsResponse.data) {
        // Backend returns { results: [...] }, extract the array
        const parentsArray = Array.isArray(parentsResponse.data)
          ? parentsResponse.data
          : (parentsResponse.data as any).results || [];
        setParents(parentsArray);
      }
    } catch (err) {
      logger.error('Error loading selection data:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      let response;

      switch (user.role) {
        case 'student':
          // Валидация для студента
          if (!studentForm.grade) {
            setError('Класс обязателен для студента');
            setLoading(false);
            return;
          }
          response = await adminAPI.updateStudentProfile(user.id, studentForm);
          break;

        case 'teacher':
          response = await adminAPI.updateTeacherProfile(user.id, teacherForm);
          break;

        case 'tutor':
          // Валидация для тьютора
          if (!tutorForm.specialization) {
            setError('Специализация обязательна для тьютора');
            setLoading(false);
            return;
          }
          response = await adminAPI.updateTutorProfile(user.id, tutorForm);
          break;

        case 'parent':
          // Для родителей пока нет полей
          response = await adminAPI.updateParentProfile(user.id, {});
          break;

        default:
          setError('Неизвестная роль пользователя');
          setLoading(false);
          return;
      }

      if (response.success) {
        toast.success('Профиль успешно обновлен');
        onSuccess();
        onOpenChange(false);
      } else {
        setError(response.error || 'Ошибка обновления профиля');
      }
    } catch (err: any) {
      setError(err?.message || 'Произошла ошибка при обновлении профиля');
    } finally {
      setLoading(false);
    }
  };

  const renderStudentFields = () => (
    <>
      <div className="space-y-2">
        <Label htmlFor="grade">Класс *</Label>
        <Input
          id="grade"
          value={studentForm.grade}
          onChange={(e) => setStudentForm({ ...studentForm, grade: e.target.value })}
          required
          disabled={loading}
          placeholder="Например: 10"
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="goal">Цель обучения</Label>
          <Badge variant="outline" className="text-xs">
            Приватное
          </Badge>
          <PrivateFieldTooltip role="student" field="goal" />
        </div>
        <Textarea
          id="goal"
          value={studentForm.goal}
          onChange={(e) => setStudentForm({ ...studentForm, goal: e.target.value })}
          disabled={loading}
          placeholder="Цель обучения студента"
          rows={3}
        />
        <p className="text-xs text-muted-foreground">
          Видят: преподаватели, тьюторы, администраторы. Студент не видит это поле.
        </p>
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="tutor">Тьютор</Label>
          <Badge variant="outline" className="text-xs">
            Приватное
          </Badge>
          <PrivateFieldTooltip role="student" field="tutor_id" />
        </div>
        <Select
          value={studentForm.tutor_id?.toString() || 'none'}
          onValueChange={(value) => setStudentForm({ ...studentForm, tutor_id: value === 'none' ? null : parseInt(value) })}
          disabled={loading}
        >
          <SelectTrigger id="tutor">
            <SelectValue placeholder="Выберите тьютора" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Не назначен</SelectItem>
            {tutors.map((tutor) => (
              <SelectItem key={tutor.id} value={tutor.id.toString()}>
                {tutor.user.full_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Студент не видит кто его тьютор.
        </p>
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="parent">Родитель</Label>
          <Badge variant="outline" className="text-xs">
            Приватное
          </Badge>
          <PrivateFieldTooltip role="student" field="parent_id" />
        </div>
        <Select
          value={studentForm.parent_id?.toString() || 'none'}
          onValueChange={(value) => setStudentForm({ ...studentForm, parent_id: value === 'none' ? null : parseInt(value) })}
          disabled={loading}
        >
          <SelectTrigger id="parent">
            <SelectValue placeholder="Выберите родителя" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Не назначен</SelectItem>
            {parents.map((parent) => (
              <SelectItem key={parent.id} value={parent.id.toString()}>
                {parent.user.full_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Студент не видит кто его родитель.
        </p>
      </div>
    </>
  );

  const renderTeacherFields = () => (
    <>
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="experience_years">Опыт работы (лет)</Label>
          <Badge variant="outline" className="text-xs">
            Приватное (только админы)
          </Badge>
          <PrivateFieldTooltip role="teacher" field="experience_years" />
        </div>
        <Input
          id="experience_years"
          type="number"
          value={teacherForm.experience_years}
          onChange={(e) => setTeacherForm({ ...teacherForm, experience_years: parseInt(e.target.value) || 0 })}
          disabled={loading}
          min="0"
        />
        <p className="text-xs text-muted-foreground">
          Преподаватель не видит это поле в своем профиле.
        </p>
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="bio">Биография</Label>
          <Badge variant="outline" className="text-xs">
            Приватное (только админы)
          </Badge>
          <PrivateFieldTooltip role="teacher" field="bio" />
        </div>
        <Textarea
          id="bio"
          value={teacherForm.bio}
          onChange={(e) => setTeacherForm({ ...teacherForm, bio: e.target.value })}
          disabled={loading}
          placeholder="Расскажите о преподавателе"
          rows={4}
        />
        <p className="text-xs text-muted-foreground">
          Преподаватель не видит это поле в своем профиле.
        </p>
      </div>
    </>
  );

  const renderTutorFields = () => (
    <>
      <div className="space-y-2">
        <Label htmlFor="specialization">Специализация *</Label>
        <Input
          id="specialization"
          value={tutorForm.specialization}
          onChange={(e) => setTutorForm({ ...tutorForm, specialization: e.target.value })}
          required
          disabled={loading}
          placeholder="Например: Математика"
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="experience_years">Опыт работы (лет)</Label>
          <Badge variant="outline" className="text-xs">
            Приватное (только админы)
          </Badge>
          <PrivateFieldTooltip role="tutor" field="experience_years" />
        </div>
        <Input
          id="experience_years"
          type="number"
          value={tutorForm.experience_years}
          onChange={(e) => setTutorForm({ ...tutorForm, experience_years: parseInt(e.target.value) || 0 })}
          disabled={loading}
          min="0"
        />
        <p className="text-xs text-muted-foreground">
          Тьютор не видит это поле в своем профиле.
        </p>
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="bio">Биография</Label>
          <Badge variant="outline" className="text-xs">
            Приватное (только админы)
          </Badge>
          <PrivateFieldTooltip role="tutor" field="bio" />
        </div>
        <Textarea
          id="bio"
          value={tutorForm.bio}
          onChange={(e) => setTutorForm({ ...tutorForm, bio: e.target.value })}
          disabled={loading}
          placeholder="Расскажите о тьюторе"
          rows={4}
        />
        <p className="text-xs text-muted-foreground">
          Тьютор не видит это поле в своем профиле.
        </p>
      </div>
    </>
  );

  const renderParentFields = () => (
    <div className="py-4 text-center text-muted-foreground">
      Для родителей пока нет редактируемых полей профиля
    </div>
  );

  const getRoleDisplayName = (role: string) => {
    const roleNames: Record<string, string> = {
      student: 'студента',
      teacher: 'преподавателя',
      tutor: 'тьютора',
      parent: 'родителя',
    };
    return roleNames[role] || role;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Редактировать профиль {getRoleDisplayName(user.role)}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            {user.role === 'student' && renderStudentFields()}
            {user.role === 'teacher' && renderTeacherFields()}
            {user.role === 'tutor' && renderTutorFields()}
            {user.role === 'parent' && renderParentFields()}
          </div>

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <DialogFooter>
            <Button type="button"
              variant="outline"
              type="button"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Отмена
            </Button>
            <Button type="submit" disabled={loading || user.role === 'parent'}>
              {loading ? 'Сохранение...' : 'Сохранить'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
