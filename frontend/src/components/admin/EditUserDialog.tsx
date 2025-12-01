import { useState, useEffect } from 'react';
import { User } from '@/integrations/api/unifiedClient';
import {
  adminAPI,
  UserUpdateData,
  StudentProfileData,
  TeacherProfileData,
  TutorProfileData,
  Tutor,
  Parent,
} from '@/integrations/api/adminAPI';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

interface EditUserDialogProps {
  user: User;
  profile?: any;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export const EditUserDialog = ({ user, profile, open, onOpenChange, onSuccess }: EditUserDialogProps) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tutors, setTutors] = useState<Tutor[]>([]);
  const [parents, setParents] = useState<Parent[]>([]);

  const [formData, setFormData] = useState<UserUpdateData>({
    email: user.email,
    first_name: user.first_name,
    last_name: user.last_name,
    phone: user.phone || '',
    is_active: user.is_active !== false,
  });

  const [studentProfile, setStudentProfile] = useState<StudentProfileData>({
    grade: profile?.grade || '',
    goal: profile?.goal || '',
    tutor_id: profile?.tutor_id || profile?.tutor?.id || null,
    parent_id: profile?.parent_id || profile?.parent?.id || null,
  });

  const [teacherProfile, setTeacherProfile] = useState<TeacherProfileData>({
    experience_years: profile?.experience_years || 0,
    bio: profile?.bio || '',
  });

  const [tutorProfile, setTutorProfile] = useState<TutorProfileData>({
    specialization: profile?.specialization || '',
    experience_years: profile?.experience_years || 0,
    bio: profile?.bio || '',
  });

  useEffect(() => {
    if (user.role === 'student' && open) {
      loadSelectionData();
    }
  }, [user.role, open]);

  useEffect(() => {
    setFormData({
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      phone: user.phone || '',
      is_active: user.is_active !== false,
    });

    if (user.role === 'student') {
      setStudentProfile({
        grade: profile?.grade || '',
        goal: profile?.goal || '',
        tutor_id: profile?.tutor_id || profile?.tutor?.id || null,
        parent_id: profile?.parent_id || profile?.parent?.id || null,
      });
    } else if (user.role === 'teacher') {
      setTeacherProfile({
        experience_years: profile?.experience_years || 0,
        bio: profile?.bio || '',
      });
    } else if (user.role === 'tutor') {
      setTutorProfile({
        specialization: profile?.specialization || '',
        experience_years: profile?.experience_years || 0,
        bio: profile?.bio || '',
      });
    }
  }, [user, profile, open]);

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
      console.error('Error loading selection data:', err);
    }
  };

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const formatPhone = (phone: string): string => {
    const digits = phone.replace(/\D/g, '');

    if (digits.startsWith('8')) {
      return '+7' + digits.slice(1);
    }

    if (digits.startsWith('7')) {
      return '+' + digits;
    }

    if (digits.length === 10) {
      return '+7' + digits;
    }

    return phone;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.email || !formData.first_name || !formData.last_name) {
      setError('Email, имя и фамилия обязательны');
      return;
    }

    if (!validateEmail(formData.email)) {
      setError('Некорректный формат email');
      return;
    }

    if (user.role === 'student' && !studentProfile.grade) {
      setError('Класс обязателен для студента');
      return;
    }

    if (user.role === 'tutor' && !tutorProfile.specialization) {
      setError('Специализация обязательна для тьютора');
      return;
    }

    setLoading(true);

    try {
      const dataToSend: UserUpdateData = {
        ...formData,
        phone: formData.phone ? formatPhone(formData.phone) : undefined,
      };

      if (user.role === 'student') {
        dataToSend.profile_data = studentProfile;
      } else if (user.role === 'teacher') {
        dataToSend.profile_data = teacherProfile;
      } else if (user.role === 'tutor') {
        dataToSend.profile_data = tutorProfile;
      }

      const response = await adminAPI.updateUser(user.id, dataToSend);

      if (response.success) {
        toast.success('Пользователь успешно обновлен');
        onSuccess();
        onOpenChange(false);
      } else {
        setError(response.error || 'Ошибка обновления пользователя');
      }
    } catch (err: any) {
      setError(err?.message || 'Произошла ошибка при обновлении пользователя');
    } finally {
      setLoading(false);
    }
  };

  const renderStudentProfileFields = () => (
    <>
      <Separator className="my-4" />
      <h3 className="text-sm font-medium mb-3">Профиль студента</h3>

      <div className="space-y-2">
        <Label htmlFor="grade">Класс *</Label>
        <Input
          id="grade"
          value={studentProfile.grade}
          onChange={(e) => setStudentProfile({ ...studentProfile, grade: e.target.value })}
          required
          disabled={loading}
          placeholder="Например: 10"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="goal">Цель обучения</Label>
        <Textarea
          id="goal"
          value={studentProfile.goal}
          onChange={(e) => setStudentProfile({ ...studentProfile, goal: e.target.value })}
          disabled={loading}
          placeholder="Цель обучения студента"
          rows={3}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="tutor">Тьютор</Label>
        <Select
          value={studentProfile.tutor_id?.toString() || 'none'}
          onValueChange={(value) =>
            setStudentProfile({ ...studentProfile, tutor_id: value === 'none' ? null : parseInt(value) })
          }
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
      </div>

      <div className="space-y-2">
        <Label htmlFor="parent">Родитель</Label>
        <Select
          value={studentProfile.parent_id?.toString() || 'none'}
          onValueChange={(value) =>
            setStudentProfile({ ...studentProfile, parent_id: value === 'none' ? null : parseInt(value) })
          }
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
      </div>
    </>
  );

  const renderTeacherProfileFields = () => (
    <>
      <Separator className="my-4" />
      <h3 className="text-sm font-medium mb-3">Профиль преподавателя</h3>

      <div className="space-y-2">
        <Label htmlFor="experience_years">Опыт работы (лет)</Label>
        <Input
          id="experience_years"
          type="number"
          value={teacherProfile.experience_years}
          onChange={(e) =>
            setTeacherProfile({ ...teacherProfile, experience_years: parseInt(e.target.value) || 0 })
          }
          disabled={loading}
          min="0"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="bio">Биография</Label>
        <Textarea
          id="bio"
          value={teacherProfile.bio}
          onChange={(e) => setTeacherProfile({ ...teacherProfile, bio: e.target.value })}
          disabled={loading}
          placeholder="Расскажите о преподавателе"
          rows={4}
        />
      </div>
    </>
  );

  const renderTutorProfileFields = () => (
    <>
      <Separator className="my-4" />
      <h3 className="text-sm font-medium mb-3">Профиль тьютора</h3>

      <div className="space-y-2">
        <Label htmlFor="specialization">Специализация *</Label>
        <Input
          id="specialization"
          value={tutorProfile.specialization}
          onChange={(e) => setTutorProfile({ ...tutorProfile, specialization: e.target.value })}
          required
          disabled={loading}
          placeholder="Например: Математика"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="experience_years">Опыт работы (лет)</Label>
        <Input
          id="experience_years"
          type="number"
          value={tutorProfile.experience_years}
          onChange={(e) =>
            setTutorProfile({ ...tutorProfile, experience_years: parseInt(e.target.value) || 0 })
          }
          disabled={loading}
          min="0"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="bio">Биография</Label>
        <Textarea
          id="bio"
          value={tutorProfile.bio}
          onChange={(e) => setTutorProfile({ ...tutorProfile, bio: e.target.value })}
          disabled={loading}
          placeholder="Расскажите о тьюторе"
          rows={4}
        />
      </div>
    </>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Редактировать пользователя</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <h3 className="text-sm font-medium">Базовая информация</h3>

            <div className="space-y-2">
              <Label htmlFor="email">Email *</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                disabled={loading}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="first_name">Имя *</Label>
                <Input
                  id="first_name"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  required
                  disabled={loading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="last_name">Фамилия *</Label>
                <Input
                  id="last_name"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  required
                  disabled={loading}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Телефон</Label>
              <Input
                id="phone"
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="+7XXXXXXXXXX"
                disabled={loading}
              />
              <p className="text-xs text-muted-foreground">Формат: +7XXXXXXXXXX</p>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="is_active"
                checked={formData.is_active}
                onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                disabled={loading}
              />
              <Label htmlFor="is_active" className="cursor-pointer">
                Активен
              </Label>
            </div>

            {user.role === 'student' && renderStudentProfileFields()}
            {user.role === 'teacher' && renderTeacherProfileFields()}
            {user.role === 'tutor' && renderTutorProfileFields()}
          </div>

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <DialogFooter>
            <Button variant="outline" type="button" onClick={() => onOpenChange(false)} disabled={loading}>
              Отмена
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Сохранение...' : 'Сохранить'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
