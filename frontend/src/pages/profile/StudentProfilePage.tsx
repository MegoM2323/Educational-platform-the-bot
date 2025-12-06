import { useState, useEffect } from 'react';
import { logger } from '@/utils/logger';
import { useNavigate } from 'react-router-dom';
import { useStudentProfile } from '@/hooks/useStudentProfile';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { ChevronLeft, Upload, X } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

export const StudentProfilePage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { profile, isLoading, updateProfile, isUpdating } = useStudentProfile();

  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    grade: '',
    goal: '',
    telegram: '',
  });

  const [initialData, setInitialData] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    grade: '',
    goal: '',
    telegram: '',
  });

  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [charCount, setCharCount] = useState(0);
  const maxGoalChars = 500;

  useEffect(() => {
    if (profile) {
      const newData = {
        first_name: profile.user?.first_name || '',
        last_name: profile.user?.last_name || '',
        phone: profile.user?.phone || '',
        grade: profile.profile?.grade || '',
        goal: profile.profile?.goal || '',
        telegram: profile.profile?.telegram || '',
      };
      setFormData(newData);
      setInitialData(newData);
      setCharCount(profile.profile?.goal?.length || 0);
    }
  }, [profile]);

  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => {
      const updated = { ...prev, [field]: value };

      // Check if ANY field has changed from the initial data
      const hasAnyChanges = Object.keys(updated).some(
        (key) => updated[key as keyof typeof updated] !== initialData[key as keyof typeof initialData]
      );
      setHasUnsavedChanges(hasAnyChanges);

      return updated;
    });

    if (field === 'goal') {
      setCharCount(value.length);
    }
  };

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      toast.error('Файл слишком большой. Максимум 5MB');
      return;
    }

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      toast.error('Неподдерживаемый формат. Используйте JPG, PNG или WebP');
      return;
    }

    setAvatarFile(file);
    const reader = new FileReader();
    reader.onloadend = () => {
      setAvatarPreview(reader.result as string);
    };
    reader.readAsDataURL(file);
    // Avatar has changed, mark as unsaved
    setHasUnsavedChanges(true);
  };

  const handleRemoveAvatar = () => {
    setAvatarFile(null);
    setAvatarPreview(null);
    // Mark as changed only if there was an avatar to remove
    if (profile?.user?.avatar) {
      setHasUnsavedChanges(true);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const data = new FormData();

    // Only append fields that have changed from the initial data
    if (formData.first_name !== initialData.first_name) {
      data.append('first_name', formData.first_name);
    }
    if (formData.last_name !== initialData.last_name) {
      data.append('last_name', formData.last_name);
    }
    if (formData.phone !== initialData.phone) {
      data.append('phone', formData.phone);
    }
    // Only send grade if it was explicitly changed (not just empty)
    if (formData.grade !== initialData.grade) {
      if (formData.grade) {
        data.append('grade', formData.grade);
      } else {
        // If grade was cleared, send null to backend
        data.append('grade', '');
      }
    }
    if (formData.goal !== initialData.goal) {
      data.append('goal', formData.goal);
    }
    if (formData.telegram !== initialData.telegram) {
      data.append('telegram', formData.telegram);
    }

    if (avatarFile) {
      data.append('avatar', avatarFile);
    }

    try {
      await updateProfile(data);
      setHasUnsavedChanges(false);
      setAvatarFile(null);
      setAvatarPreview(null);
    } catch (error) {
      logger.error('Failed to update profile:', error);
    }
  };

  if (!user) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner />
      </div>
    );
  }

  const initials = `${formData.first_name[0] || ''}${formData.last_name[0] || ''}`.toUpperCase();
  const currentAvatar = avatarPreview || profile?.user?.avatar;

  return (
    <div className="min-h-screen bg-[hsl(240,20%,99%)] py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6 flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(-1)}
            aria-label="Вернуться на предыдущую страницу"
          >
            <ChevronLeft className="w-4 h-4 mr-2" />
            Назад
          </Button>
        </div>

        <div className="mb-6">
          <h1 className="text-3xl font-bold text-[hsl(240,10%,15%)] mb-2">Мой профиль</h1>
          <p className="text-[hsl(240,5%,45%)]">
            Здесь вы можете редактировать информацию о себе
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-1">
              <div className="sticky top-4">
                <Card className="shadow-md">
                  <CardContent className="p-6 flex flex-col items-center gap-4">
                    <Avatar className="w-48 h-48 shadow-lg border-4 border-[hsl(0,0%,96%)]">
                      <AvatarImage src={currentAvatar} alt={`${formData.first_name} ${formData.last_name}`} />
                      <AvatarFallback
                        className="text-6xl font-bold text-white"
                        style={{
                          background: 'linear-gradient(135deg, hsl(250, 70%, 60%), hsl(270, 80%, 70%))',
                        }}
                      >
                        {initials}
                      </AvatarFallback>
                    </Avatar>

                    <div className="w-full">
                      <label
                        htmlFor="avatar-upload"
                        className={cn(
                          'flex flex-col items-center justify-center w-full p-6 border-2 border-dashed rounded-lg cursor-pointer transition-all',
                          'border-[hsl(240,10%,90%)] bg-[hsl(240,10%,98%)]',
                          'hover:border-[hsl(250,70%,60%)] hover:bg-[hsl(250,70%,98%)]'
                        )}
                      >
                        <Upload className="w-8 h-8 mb-2 text-[hsl(240,5%,45%)]" />
                        <span className="text-sm text-[hsl(240,5%,45%)]">
                          {avatarFile ? avatarFile.name : 'Загрузить фото'}
                        </span>
                        <span className="text-xs text-[hsl(240,5%,60%)] mt-1">
                          JPG, PNG, WebP (макс. 5MB)
                        </span>
                        <input
                          id="avatar-upload"
                          type="file"
                          className="hidden"
                          accept="image/jpeg,image/png,image/webp"
                          onChange={handleAvatarChange}
                        />
                      </label>

                      {avatarPreview && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="w-full mt-2"
                          onClick={handleRemoveAvatar}
                        >
                          <X className="w-4 h-4 mr-2" />
                          Отменить
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>

            <div className="lg:col-span-2">
              <Card className="shadow-md">
                <CardHeader>
                  <CardTitle className="text-2xl">Профиль студента</CardTitle>
                  <CardDescription>
                    Обновите вашу персональную информацию
                  </CardDescription>
                </CardHeader>

                <CardContent className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="first_name" className="text-sm font-medium">
                        Имя <span className="text-[hsl(0,84%,60%)]">*</span>
                      </Label>
                      <Input
                        id="first_name"
                        value={formData.first_name}
                        onChange={(e) => handleInputChange('first_name', e.target.value)}
                        required
                        className="h-10"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="last_name" className="text-sm font-medium">
                        Фамилия <span className="text-[hsl(0,84%,60%)]">*</span>
                      </Label>
                      <Input
                        id="last_name"
                        value={formData.last_name}
                        onChange={(e) => handleInputChange('last_name', e.target.value)}
                        required
                        className="h-10"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-sm font-medium">
                      Email
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      value={profile?.user?.email || ''}
                      disabled
                      className="h-10 bg-[hsl(240,10%,96%)] opacity-50 cursor-not-allowed"
                    />
                    <p className="text-xs text-[hsl(240,5%,55%)]">Email нельзя изменить</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="phone" className="text-sm font-medium">
                      Телефон
                    </Label>
                    <Input
                      id="phone"
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => handleInputChange('phone', e.target.value)}
                      placeholder="+7 (999) 123-45-67"
                      className="h-10"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="grade" className="text-sm font-medium">
                      Класс <span className="text-[hsl(0,84%,60%)]">*</span>
                    </Label>
                    <Select value={formData.grade} onValueChange={(value) => handleInputChange('grade', value)}>
                      <SelectTrigger className="h-10">
                        <SelectValue placeholder="Выберите класс" />
                      </SelectTrigger>
                      <SelectContent>
                        {Array.from({ length: 12 }, (_, i) => i + 1).map((grade) => (
                          <SelectItem key={grade} value={String(grade)}>
                            {grade} класс
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-[hsl(240,5%,55%)]">Введите номер класса (1-12)</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="goal" className="text-sm font-medium">
                      Цель обучения
                    </Label>
                    <Textarea
                      id="goal"
                      value={formData.goal}
                      onChange={(e) => handleInputChange('goal', e.target.value)}
                      placeholder="Опишите свои цели в обучении..."
                      className="min-h-24 resize-none"
                      maxLength={maxGoalChars}
                      rows={4}
                    />
                    <p className="text-xs text-[hsl(240,5%,55%)] text-right">
                      Осталось: {maxGoalChars - charCount} символов
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="telegram" className="text-sm font-medium">
                      Telegram
                    </Label>
                    <Input
                      id="telegram"
                      value={formData.telegram}
                      onChange={(e) => handleInputChange('telegram', e.target.value)}
                      placeholder="@username или username"
                      className="h-10"
                    />
                    <p className="text-xs text-[hsl(240,5%,55%)]">Формат: @username или username</p>
                  </div>
                </CardContent>

                <CardFooter className="flex items-center justify-between border-t pt-6">
                  <div className="flex items-center gap-2">
                    {hasUnsavedChanges && (
                      <>
                        <div className="w-2 h-2 bg-[hsl(30,95%,60%)] rounded-full animate-pulse" />
                        <span className="text-sm text-[hsl(240,5%,45%)]">Несохраненные изменения</span>
                      </>
                    )}
                  </div>

                  <Button
                    type="submit"
                    disabled={isUpdating}
                    className="bg-[hsl(250,70%,60%)] hover:bg-[hsl(250,70%,55%)] text-white shadow-sm hover:shadow-md transition-all"
                  >
                    {isUpdating ? (
                      <>
                        <LoadingSpinner className="w-4 h-4 mr-2" />
                        Сохранение...
                      </>
                    ) : (
                      'Сохранить'
                    )}
                  </Button>
                </CardFooter>
              </Card>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default StudentProfilePage;
