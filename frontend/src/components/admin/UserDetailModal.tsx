import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { toast } from 'sonner';
import { logger } from '@/utils/logger';
import { unifiedAPI, User } from '@/integrations/api/unifiedClient';
import { adminAPI } from '@/integrations/api/adminAPI';
import { EditUserDialog } from '@/components/admin/EditUserDialog';
import { DeleteUserDialog } from '@/components/admin/DeleteUserDialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Edit, Trash2, X, Calendar, DollarSign, FileText, BookOpen } from 'lucide-react';

/**
 * Типы для профилей (из API contracts)
 */
interface StudentProfileData {
  id: number;
  grade?: string;
  goal?: string;
  tutor?: { id: number; name: string } | null;
  parent?: { id: number; name: string } | null;
  progress_percentage?: number;
  streak_days?: number;
  total_points?: number;
  accuracy_percentage?: number;
  telegram?: string;
}

interface TeacherProfileData {
  id: number;
  subject?: string;
  experience_years?: number;
  bio?: string;
  telegram?: string;
  subjects?: Array<{ id: number; name: string }>;
}

interface TutorProfileData {
  id: number;
  specialization?: string;
  experience_years?: number;
  bio?: string;
  telegram?: string;
}

interface ParentProfileData {
  id: number;
  telegram?: string;
}

interface UserProfileResponse {
  user: User & {
    created_at?: string;
  };
  profile: StudentProfileData | TeacherProfileData | TutorProfileData | ParentProfileData | null;
}

interface Enrollment {
  id: number;
  subject: string | null;
  teacher: string | null;
  tutor: string | null;
  enrolled_at: string | null;
}

interface ScheduleItem {
  id: string;
  title: string;
  subject: string | null;
  date: string | null;
  start_time: string | null;
  end_time: string | null;
  student: string | null;
  teacher: string | null;
}

interface Invoice {
  id: number;
  amount: number;
  status: string;
  student: string | null;
  tutor: string | null;
  created_at: string | null;
  due_date: string | null;
}

interface Report {
  id: number;
  type: string;
  status?: string;
  created_at: string | null;
}

interface UserFullInfoResponse {
  user: User & {
    created_at?: string;
    updated_at?: string;
    is_verified?: boolean;
  };
  profile: StudentProfileData | TeacherProfileData | TutorProfileData | ParentProfileData | null;
  enrollments: Enrollment[];
  schedule: ScheduleItem[];
  invoices: Invoice[];
  reports: Report[];
}

interface UserDetailModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userId: number;
  role: 'student' | 'teacher' | 'tutor' | 'parent';
  onUpdate?: () => void;
}

/**
 * Модальное окно для просмотра детальной информации о пользователе
 *
 * Показывает:
 * - Базовую информацию (User)
 * - Профиль по роли (StudentProfile, TeacherProfile, TutorProfile, ParentProfile)
 * - Дополнительную информацию (enrollments, schedule, invoices, reports)
 *
 * Функционал:
 * - Просмотр всех данных
 * - Редактирование (через EditUserDialog)
 * - Удаление (через DeleteUserDialog)
 */
export default function UserDetailModal({
  open,
  onOpenChange,
  userId,
  role,
  onUpdate,
}: UserDetailModalProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [profileData, setProfileData] = useState<UserProfileResponse | null>(null);
  const [fullInfo, setFullInfo] = useState<UserFullInfoResponse | null>(null);
  const [activeTab, setActiveTab] = useState('profile');

  // Диалоги
  const [editDialog, setEditDialog] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState(false);

  // Загрузка данных профиля
  const loadProfileData = async () => {
    setIsLoading(true);
    try {
      const response = await unifiedAPI.request<UserProfileResponse>(
        `/accounts/admin/users/${userId}/profile/`
      );
      if (response.success && response.data) {
        setProfileData(response.data);
      } else {
        toast.error(response.error || 'Ошибка загрузки профиля');
      }
    } catch (error) {
      logger.error('[UserDetailModal] Error loading profile:', error);
      toast.error('Не удалось загрузить профиль');
    } finally {
      setIsLoading(false);
    }
  };

  // Загрузка полной информации
  const loadFullInfo = async () => {
    try {
      const response = await unifiedAPI.request<UserFullInfoResponse>(
        `/accounts/admin/users/${userId}/full-info/`
      );
      if (response.success && response.data) {
        setFullInfo(response.data);
      }
    } catch (error) {
      logger.error('[UserDetailModal] Error loading full info:', error);
    }
  };

  useEffect(() => {
    if (open && userId) {
      loadProfileData();
      loadFullInfo();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, userId]);

  const handleEditSuccess = () => {
    loadProfileData();
    loadFullInfo();
    onUpdate?.();
  };

  const handleDeleteSuccess = () => {
    onOpenChange(false);
    onUpdate?.();
  };

  const user = profileData?.user;
  const profile = profileData?.profile;

  const getAvatarFallback = () => {
    if (!user) return 'U';
    const firstName = user.first_name || '';
    const lastName = user.last_name || '';
    return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase() || 'U';
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>Профиль пользователя</span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => onOpenChange(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </DialogTitle>
          </DialogHeader>

          {isLoading ? (
            <div className="py-12 text-center text-muted-foreground">Загрузка...</div>
          ) : !user ? (
            <div className="py-12 text-center text-muted-foreground">
              Пользователь не найден
            </div>
          ) : (
            <div className="space-y-6">
              {/* Шапка с аватаром и основной информацией */}
              <div className="flex items-start gap-6">
                <Avatar className="h-24 w-24">
                  <AvatarImage src={user.avatar} alt={user.full_name} />
                  <AvatarFallback className="text-2xl">
                    {getAvatarFallback()}
                  </AvatarFallback>
                </Avatar>

                <div className="flex-1 space-y-2">
                  <h3 className="text-2xl font-semibold">{user.full_name}</h3>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant={user.is_active ? 'default' : 'secondary'}>
                      {user.is_active ? 'Активен' : 'Неактивен'}
                    </Badge>
                    <Badge variant="outline">{user.role_display}</Badge>
                  </div>
                  <div className="text-sm text-muted-foreground space-y-1">
                    <p>Email: {user.email}</p>
                    {user.phone && <p>Телефон: {user.phone}</p>}
                    {user.created_at && (
                      <p>
                        Зарегистрирован:{' '}
                        {new Date(user.created_at).toLocaleDateString('ru-RU')}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <Separator />

              {/* Табы с дополнительной информацией */}
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="profile">Профиль</TabsTrigger>
                  <TabsTrigger value="enrollments">
                    <BookOpen className="h-4 w-4 mr-2" />
                    Предметы
                  </TabsTrigger>
                  <TabsTrigger value="schedule">
                    <Calendar className="h-4 w-4 mr-2" />
                    Расписание
                  </TabsTrigger>
                  <TabsTrigger value="other">
                    <FileText className="h-4 w-4 mr-2" />
                    Другое
                  </TabsTrigger>
                </TabsList>

                {/* Профиль */}
                <TabsContent value="profile" className="space-y-4">
                  {role === 'student' && profile && 'grade' in profile && (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Класс</p>
                        <p className="text-base">{profile.grade || '-'}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Цель</p>
                        <p className="text-base">{profile.goal || '-'}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Тьютор</p>
                        <p className="text-base">
                          {profile.tutor ? profile.tutor.name : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Родитель</p>
                        <p className="text-base">
                          {profile.parent ? profile.parent.name : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Прогресс</p>
                        <p className="text-base">
                          {profile.progress_percentage ?? 0}%
                        </p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Дни подряд</p>
                        <p className="text-base">{profile.streak_days ?? 0}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Баллы</p>
                        <p className="text-base">{profile.total_points ?? 0}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Точность</p>
                        <p className="text-base">
                          {profile.accuracy_percentage ?? 0}%
                        </p>
                      </div>
                    </div>
                  )}

                  {role === 'teacher' && profile && 'subject' in profile && (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Предмет</p>
                        <p className="text-base">{profile.subject || '-'}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Опыт (лет)</p>
                        <p className="text-base">{profile.experience_years ?? 0}</p>
                      </div>
                      <div className="col-span-2">
                        <p className="text-sm font-medium text-muted-foreground">Био</p>
                        <p className="text-base">{profile.bio || '-'}</p>
                      </div>
                      {profile.subjects && profile.subjects.length > 0 && (
                        <div className="col-span-2">
                          <p className="text-sm font-medium text-muted-foreground mb-2">
                            Предметы
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {profile.subjects.map((subject) => (
                              <Badge key={subject.id} variant="secondary">
                                {subject.name}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {role === 'tutor' && profile && 'specialization' in profile && (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">
                          Специализация
                        </p>
                        <p className="text-base">{profile.specialization || '-'}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Опыт (лет)</p>
                        <p className="text-base">{profile.experience_years ?? 0}</p>
                      </div>
                      <div className="col-span-2">
                        <p className="text-sm font-medium text-muted-foreground">Био</p>
                        <p className="text-base">{profile.bio || '-'}</p>
                      </div>
                    </div>
                  )}

                  {role === 'parent' && (
                    <div className="text-sm text-muted-foreground">
                      <p>Профиль родителя (базовые поля отображены выше)</p>
                    </div>
                  )}

                  {/* Telegram для всех ролей */}
                  {profile && 'telegram' in profile && profile.telegram && (
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Telegram</p>
                      <p className="text-base">{profile.telegram}</p>
                    </div>
                  )}
                </TabsContent>

                {/* Предметы (для студентов) */}
                <TabsContent value="enrollments" className="space-y-4">
                  {fullInfo?.enrollments && fullInfo.enrollments.length > 0 ? (
                    <div className="space-y-2">
                      {fullInfo.enrollments.map((enrollment) => (
                        <div
                          key={enrollment.id}
                          className="p-3 border rounded-md space-y-1"
                        >
                          <p className="font-medium">{enrollment.subject || '-'}</p>
                          <p className="text-sm text-muted-foreground">
                            Преподаватель: {enrollment.teacher || '-'}
                          </p>
                          {enrollment.tutor && (
                            <p className="text-sm text-muted-foreground">
                              Тьютор: {enrollment.tutor}
                            </p>
                          )}
                          {enrollment.enrolled_at && (
                            <p className="text-xs text-muted-foreground">
                              Зачислен:{' '}
                              {new Date(enrollment.enrolled_at).toLocaleDateString('ru-RU')}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      Нет назначенных предметов
                    </p>
                  )}
                </TabsContent>

                {/* Расписание */}
                <TabsContent value="schedule" className="space-y-4">
                  {fullInfo?.schedule && fullInfo.schedule.length > 0 ? (
                    <div className="space-y-2">
                      {fullInfo.schedule.map((lesson) => (
                        <div
                          key={lesson.id}
                          className="p-3 border rounded-md space-y-1"
                        >
                          <p className="font-medium">{lesson.title || 'Урок'}</p>
                          <p className="text-sm">Предмет: {lesson.subject || '-'}</p>
                          {lesson.date && (
                            <p className="text-sm">
                              Дата: {new Date(lesson.date).toLocaleDateString('ru-RU')}
                            </p>
                          )}
                          {lesson.start_time && lesson.end_time && (
                            <p className="text-sm">
                              Время: {lesson.start_time} - {lesson.end_time}
                            </p>
                          )}
                          {lesson.student && (
                            <p className="text-sm text-muted-foreground">
                              Студент: {lesson.student}
                            </p>
                          )}
                          {lesson.teacher && (
                            <p className="text-sm text-muted-foreground">
                              Преподаватель: {lesson.teacher}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      Нет запланированных уроков
                    </p>
                  )}
                </TabsContent>

                {/* Другое (инвойсы, отчёты) */}
                <TabsContent value="other" className="space-y-4">
                  {/* Инвойсы (для родителей) */}
                  {role === 'parent' && fullInfo?.invoices && fullInfo.invoices.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2 flex items-center gap-2">
                        <DollarSign className="h-4 w-4" />
                        Счета
                      </h4>
                      <div className="space-y-2">
                        {fullInfo.invoices.map((invoice) => (
                          <div
                            key={invoice.id}
                            className="p-3 border rounded-md space-y-1"
                          >
                            <div className="flex justify-between items-start">
                              <p className="font-medium">{invoice.amount} ₽</p>
                              <Badge
                                variant={
                                  invoice.status === 'paid'
                                    ? 'default'
                                    : invoice.status === 'sent'
                                    ? 'secondary'
                                    : 'outline'
                                }
                              >
                                {invoice.status}
                              </Badge>
                            </div>
                            {invoice.student && (
                              <p className="text-sm">Студент: {invoice.student}</p>
                            )}
                            {invoice.tutor && (
                              <p className="text-sm text-muted-foreground">
                                Тьютор: {invoice.tutor}
                              </p>
                            )}
                            {invoice.due_date && (
                              <p className="text-xs text-muted-foreground">
                                Срок: {new Date(invoice.due_date).toLocaleDateString('ru-RU')}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Отчёты */}
                  {fullInfo?.reports && fullInfo.reports.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2 flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        Отчёты
                      </h4>
                      <div className="space-y-2">
                        {fullInfo.reports.map((report) => (
                          <div
                            key={report.id}
                            className="p-3 border rounded-md space-y-1"
                          >
                            <div className="flex justify-between items-start">
                              <p className="font-medium">
                                {report.type === 'tutor_weekly'
                                  ? 'Еженедельный отчёт тьютора'
                                  : 'Отчёт преподавателя'}
                              </p>
                              {report.status && (
                                <Badge variant="outline">{report.status}</Badge>
                              )}
                            </div>
                            {report.created_at && (
                              <p className="text-xs text-muted-foreground">
                                Создан:{' '}
                                {new Date(report.created_at).toLocaleDateString('ru-RU')}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {(!fullInfo?.invoices || fullInfo.invoices.length === 0) &&
                    (!fullInfo?.reports || fullInfo.reports.length === 0) && (
                      <p className="text-sm text-muted-foreground text-center py-8">
                        Нет дополнительных данных
                      </p>
                    )}
                </TabsContent>
              </Tabs>
            </div>
          )}

          <DialogFooter className="flex gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setEditDialog(true)}
              disabled={!user}
            >
              <Edit className="h-4 w-4 mr-2" />
              Редактировать
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => setDeleteDialog(true)}
              disabled={!user}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Удалить
            </Button>
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
              Закрыть
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Диалог редактирования */}
      {user && profile && (
        <EditUserDialog
          user={user}
          profile={
            role === 'student'
              ? { id: profile.id, user, ...profile }
              : role === 'teacher'
              ? { id: profile.id, user, ...profile }
              : role === 'tutor'
              ? { id: profile.id, user, ...profile }
              : { id: profile.id, user, ...profile }
          }
          open={editDialog}
          onOpenChange={setEditDialog}
          onSuccess={handleEditSuccess}
        />
      )}

      {/* Диалог удаления */}
      {user && (
        <DeleteUserDialog
          user={user}
          open={deleteDialog}
          onOpenChange={setDeleteDialog}
          onSuccess={handleDeleteSuccess}
        />
      )}
    </>
  );
}
