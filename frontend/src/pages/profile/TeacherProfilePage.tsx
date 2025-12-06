import { useState, useEffect } from 'react';
import { logger } from '@/utils/logger';
import { useNavigate } from 'react-router-dom';
import { useTeacherProfile } from '@/hooks/useTeacherProfile';
import { useAuth } from '@/hooks/useAuth';
import { useQuery } from '@tanstack/react-query';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { ChevronLeft, Upload, X, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface Subject {
  id: number;
  name: string;
  color?: string;
}

export const TeacherProfilePage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { profile, isLoading, updateProfile, isUpdating } = useTeacherProfile();

  const { data: allSubjects } = useQuery({
    queryKey: ['allSubjects'],
    queryFn: async () => {
      const response = await unifiedAPI.request<{ success: boolean; count: number; results: Subject[] }>('/materials/subjects/all/');
      if (!response.success || !response.data) {
        throw new Error('Failed to load subjects');
      }
      // Backend returns {success: true, count: 5, results: [...]}
      // Extract the results array
      const data = response.data as any;
      return Array.isArray(data) ? data : (data.results || []);
    },
  });

  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    experience_years: 0,
    bio: '',
    telegram: '',
  });

  const [selectedSubjects, setSelectedSubjects] = useState<number[]>([]);
  const [subjectToAdd, setSubjectToAdd] = useState<string>('');
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [charCount, setCharCount] = useState(0);
  const maxBioChars = 1000;

  useEffect(() => {
    if (profile) {
      setFormData({
        first_name: profile.user?.first_name || '',
        last_name: profile.user?.last_name || '',
        phone: profile.user?.phone || '',
        experience_years: profile.profile?.experience_years || 0,
        bio: profile.profile?.bio || '',
        telegram: profile.profile?.telegram || '',
      });
      setCharCount(profile.profile?.bio?.length || 0);

      if (profile.profile?.subjects_list && allSubjects && Array.isArray(allSubjects)) {
        const subjectNames = profile.profile.subjects_list;
        const subjectIds = allSubjects
          .filter((s) => subjectNames.includes(s.name))
          .map((s) => s.id);
        setSelectedSubjects(subjectIds);
      }
    }
  }, [profile, allSubjects]);

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

  const handleInputChange = (field: string, value: string | number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setHasUnsavedChanges(true);

    if (field === 'bio' && typeof value === 'string') {
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
    setHasUnsavedChanges(true);
  };

  const handleRemoveAvatar = () => {
    setAvatarFile(null);
    setAvatarPreview(null);
    setHasUnsavedChanges(true);
  };

  const handleAddSubject = () => {
    if (!subjectToAdd) return;

    const subjectId = parseInt(subjectToAdd);
    if (selectedSubjects.includes(subjectId)) {
      toast.error('Этот предмет уже добавлен');
      return;
    }

    setSelectedSubjects((prev) => [...prev, subjectId]);
    setSubjectToAdd('');
    setHasUnsavedChanges(true);
  };

  const handleRemoveSubject = (subjectId: number) => {
    setSelectedSubjects((prev) => prev.filter((id) => id !== subjectId));
    setHasUnsavedChanges(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const data = new FormData();
    data.append('first_name', formData.first_name);
    data.append('last_name', formData.last_name);
    data.append('phone', formData.phone);
    data.append('experience_years', String(formData.experience_years));
    data.append('bio', formData.bio);
    data.append('telegram', formData.telegram);
    data.append('subject_ids', JSON.stringify(selectedSubjects));

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

  const getSubjectNameById = (id: number) => {
    if (!Array.isArray(allSubjects)) return 'Unknown';
    return allSubjects.find((s) => s.id === id)?.name || 'Unknown';
  };

  return (
    <div className="min-h-screen bg-[hsl(240,20%,99%)] py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6 flex items-center gap-4">
          <Button type="button"
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
                          background: 'linear-gradient(135deg, hsl(160, 60%, 50%), hsl(180, 70%, 60%))',
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
                        <Button type="button"
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
                  <CardTitle className="text-2xl">Профиль преподавателя</CardTitle>
                  <CardDescription>
                    Обновите вашу персональную информацию и предметы
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
                    <Label htmlFor="experience_years" className="text-sm font-medium">
                      Опыт работы (лет)
                    </Label>
                    <Input
                      id="experience_years"
                      type="number"
                      min="0"
                      max="80"
                      value={formData.experience_years}
                      onChange={(e) => handleInputChange('experience_years', parseInt(e.target.value) || 0)}
                      className="h-10"
                    />
                    <p className="text-xs text-[hsl(240,5%,55%)]">Количество лет преподавания</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="bio" className="text-sm font-medium">
                      Биография
                    </Label>
                    <Textarea
                      id="bio"
                      value={formData.bio}
                      onChange={(e) => handleInputChange('bio', e.target.value)}
                      placeholder="Расскажите о своем опыте преподавания..."
                      className="min-h-32 resize-none"
                      maxLength={maxBioChars}
                      rows={6}
                    />
                    <p className="text-xs text-[hsl(240,5%,55%)] text-right">
                      Осталось: {maxBioChars - charCount} символов
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-sm font-medium">
                      Предметы
                    </Label>
                    <p className="text-xs text-[hsl(240,5%,55%)]">
                      Выберите предметы, которые вы преподаёте
                    </p>

                    <div className="flex gap-2">
                      <Select value={subjectToAdd} onValueChange={setSubjectToAdd}>
                        <SelectTrigger className="h-10 flex-1">
                          <SelectValue placeholder="Выберите предмет" />
                        </SelectTrigger>
                        <SelectContent>
                          {Array.isArray(allSubjects) && allSubjects.map((subject) => (
                            <SelectItem key={subject.id} value={String(subject.id)}>
                              {subject.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button type="button"
                        variant="outline"
                        onClick={handleAddSubject}
                        disabled={!subjectToAdd}
                        className="h-10"
                      >
                        <Plus className="w-4 h-4 mr-2" />
                        Добавить
                      </Button>
                    </div>

                    <div className="flex flex-wrap gap-2 mt-3">
                      {selectedSubjects.map((subjectId) => (
                        <Badge
                          key={subjectId}
                          variant="secondary"
                          className="px-3 py-1 text-sm bg-[hsl(250,70%,95%)] text-[hsl(250,70%,40%)] hover:bg-[hsl(250,70%,90%)] transition-colors"
                        >
                          {getSubjectNameById(subjectId)}
                          <button
                            type="button"
                            onClick={() => handleRemoveSubject(subjectId)}
                            className="ml-2 hover:opacity-70 transition-opacity"
                            aria-label="Удалить предмет"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </Badge>
                      ))}
                      {selectedSubjects.length === 0 && (
                        <p className="text-sm text-[hsl(240,5%,55%)]">
                          Предметы не выбраны
                        </p>
                      )}
                    </div>
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

                  <Button type="submit"
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

export default TeacherProfilePage;
