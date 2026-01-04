import { useEffect, useState, useCallback } from 'react';
import { logger } from '@/utils/logger';
import { useNavigate } from 'react-router-dom';
import { adminAPI } from '@/integrations/api/adminAPI';
import { User } from '@/integrations/api/unifiedClient';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { EditUserDialog } from '@/components/admin/EditUserDialog';
import { ResetPasswordDialog } from '@/components/admin/ResetPasswordDialog';
import { DeleteUserDialog } from '@/components/admin/DeleteUserDialog';
import { CreateStudentDialog } from '@/components/admin/CreateStudentDialog';
import { SubjectAssignmentDialog } from '@/components/admin/SubjectAssignmentDialog';
import { User as UserIcon, Key, Trash2, Plus, LogOut, ChevronLeft, ChevronRight, Search, RotateCcw, BookOpen } from 'lucide-react';

interface StudentItem {
  id: number;
  user: User;
  grade?: string;
  tutor_id?: number | null;
  parent_id?: number | null;
}

interface PaginatedResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: StudentItem[];
}

interface StudentFiltersType {
  grade?: string;
  tutor_id?: number | null;
  search?: string;
  is_active?: boolean | null;
  ordering?: string;
  page?: number;
  page_size?: number;
}

interface StudentManagementProps {
  embedded?: boolean;
}

export default function StudentManagement({ embedded = false }: StudentManagementProps) {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [students, setStudents] = useState<StudentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLogoutLoading, setIsLogoutLoading] = useState(false);
  const [createDialog, setCreateDialog] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sortBy, setSortBy] = useState<string>('');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Списки для фильтров
  const [tutors, setTutors] = useState<Array<{ id: number; user: { full_name: string } }>>([]);
  const [parents, setParents] = useState<Array<{ id: number; user: { full_name: string } }>>([]);

  // Фильтры
  const [filters, setFilters] = useState({
    search: '',
    grade: '',
    tutor_id: '',
    parent_id: '',
    is_active: 'all' as 'all' | 'true' | 'false',
  });

  // Диалоги
  const [editUserDialog, setEditUserDialog] = useState<{
    open: boolean;
    item: StudentItem | null;
  }>({ open: false, item: null });
  const [resetPasswordDialog, setResetPasswordDialog] = useState<{
    open: boolean;
    item: StudentItem | null;
  }>({ open: false, item: null });
  const [deleteUserDialog, setDeleteUserDialog] = useState<{
    open: boolean;
    item: StudentItem | null;
  }>({ open: false, item: null });
  const [reactivateDialog, setReactivateDialog] = useState<{
    open: boolean;
    item: StudentItem | null;
    isLoading: boolean;
  }>({ open: false, item: null, isLoading: false });
  const [subjectAssignmentDialog, setSubjectAssignmentDialog] = useState<{
    open: boolean;
    item: StudentItem | null;
  }>({ open: false, item: null });

  const loadStudents = useCallback(
    async (page: number = 1) => {
      setIsLoading(true);
      try {
        const filterParams: StudentFiltersType = {};

        if (filters.search) {
          filterParams.search = filters.search;
        }
        if (filters.grade) {
          filterParams.grade = filters.grade;
        }
        if (filters.tutor_id) {
          filterParams.tutor_id = parseInt(filters.tutor_id);
        }
        if (filters.is_active !== 'all') {
          filterParams.is_active = filters.is_active === 'true';
        }
        if (sortBy) {
          const direction = sortDirection === 'desc' ? '-' : '';
          filterParams.ordering = `${direction}${sortBy}`;
        }

        filterParams.page = page;
        filterParams.page_size = pageSize;

        const response = await adminAPI.getStudents(filterParams);
        if (response.success && response.data) {
          const data = response.data as PaginatedResponse;
          setStudents(data.results || []);
          setTotalCount(data.count || 0);
          setCurrentPage(page);
        } else {
          toast.error(response.error || 'Ошибка загрузки списка студентов');
          setStudents([]);
          setTotalCount(0);
        }
      } catch (e) {
        const error = e as Error;
        toast.error(error?.message || 'Ошибка загрузки списка');
        setStudents([]);
        setTotalCount(0);
      } finally {
        setIsLoading(false);
      }
    },
    [filters, pageSize, sortBy, sortDirection]
  );

  const loadFilterData = useCallback(async () => {
    try {
      const [tutorsRes, parentsRes] = await Promise.all([
        adminAPI.getTutors(),
        adminAPI.getParents(),
      ]);

      if (tutorsRes.success && tutorsRes.data) {
        // Backend returns { results: [...] }, extract the array
        const tutorsArray = Array.isArray(tutorsRes.data)
          ? tutorsRes.data
          : (tutorsRes.data as any).results || [];
        setTutors(tutorsArray);
      }
      if (parentsRes.success && parentsRes.data) {
        // Backend returns { results: [...] }, extract the array
        const parentsArray = Array.isArray(parentsRes.data)
          ? parentsRes.data
          : (parentsRes.data as any).results || [];
        setParents(parentsArray);
      }
    } catch (error) {
      logger.error('Error loading filter data:', error);
    }
  }, []);

  useEffect(() => {
    loadStudents(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadFilterData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLogout = async () => {
    setIsLogoutLoading(true);
    try {
      await logout();
      toast.success('Вы вышли из системы');
      navigate('/auth');
    } catch (error) {
      logger.error('Logout error:', error);
      toast.error('Ошибка при выходе');
    } finally {
      setIsLogoutLoading(false);
    }
  };

  const handleReactivate = async () => {
    if (!reactivateDialog.item) return;

    setReactivateDialog((prev) => ({ ...prev, isLoading: true }));
    try {
      const response = await adminAPI.reactivateUser(reactivateDialog.item.user.id);
      if (response.success) {
        toast.success('Студент успешно активирован');
        setReactivateDialog({ open: false, item: null, isLoading: false });
        await loadStudents(currentPage);
      } else {
        toast.error(response.error || 'Ошибка при активации');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Неизвестная ошибка';
      toast.error(message);
    } finally {
      setReactivateDialog((prev) => ({ ...prev, isLoading: false }));
    }
  };

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortDirection('asc');
    }
  };

  const clearFilters = () => {
    setFilters({
      search: '',
      grade: '',
      tutor_id: '',
      parent_id: '',
      is_active: 'all',
    });
    setSortBy('');
    setSortDirection('asc');
  };

  const getSortIcon = (column: string) => {
    if (sortBy !== column) return null;
    return sortDirection === 'asc' ? ' ↑' : ' ↓';
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  const cardContent = (
    <>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Управление студентами</CardTitle>
        <div className="flex gap-2">
          <Button type="button" onClick={() => setCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Создать студента
          </Button>
          {!embedded && (
            <Button type="button"
              variant="destructive"
              onClick={handleLogout}
              disabled={isLogoutLoading}
            >
              <LogOut className="h-4 w-4 mr-2" />
              {isLogoutLoading ? 'Выход...' : 'Выйти'}
            </Button>
          )}
        </div>
      </CardHeader>
        <CardContent>
          {/* Фильтры */}
          <div className="space-y-4 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <Label className="text-sm">Поиск</Label>
                <div className="flex gap-2 mt-2">
                  <Input
                    placeholder="ФИО, email..."
                    value={filters.search}
                    onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                    className="flex-1"
                  />
                  <Button type="button" variant="outline" size="icon">
                    <Search className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div>
                <Label className="text-sm">Класс</Label>
                <Input
                  placeholder="Класс..."
                  value={filters.grade}
                  onChange={(e) => setFilters({ ...filters, grade: e.target.value })}
                  className="mt-2"
                />
              </div>

              <div>
                <Label className="text-sm">Тьютор</Label>
                <select
                  value={filters.tutor_id}
                  onChange={(e) => setFilters({ ...filters, tutor_id: e.target.value })}
                  className="w-full mt-2 h-10 px-3 border border-input bg-background rounded-md text-sm"
                >
                  <option value="">Все</option>
                  {tutors.map((tutor) => (
                    <option key={tutor.id} value={tutor.id}>
                      {tutor.user.full_name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <Label className="text-sm">Статус</Label>
                <select
                  value={filters.is_active}
                  onChange={(e) => setFilters({ ...filters, is_active: e.target.value as 'all' | 'true' | 'false' })}
                  className="w-full mt-2 h-10 px-3 border border-input bg-background rounded-md text-sm"
                >
                  <option value="all">Все</option>
                  <option value="true">Активные</option>
                  <option value="false">Неактивные</option>
                </select>
              </div>
            </div>

            <div className="flex gap-2 items-center">
              <div>
                <Label className="text-sm">Показывать по</Label>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(parseInt(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="w-[120px] mt-2 h-10 px-3 border border-input bg-background rounded-md text-sm"
                >
                  <option value="10">10</option>
                  <option value="25">25</option>
                  <option value="50">50</option>
                  <option value="100">100</option>
                </select>
              </div>
              <div className="flex-1" />
              <Button type="button" variant="outline" onClick={clearFilters} className="mt-6">
                Сбросить фильтры
              </Button>
            </div>
          </div>

          {/* Таблица */}
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left border-b">
                  <th
                    className="py-2 pr-4 cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort('user__last_name')}
                  >
                    ФИО{getSortIcon('user__last_name')}
                  </th>
                  <th
                    className="py-2 pr-4 cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort('user__email')}
                  >
                    Email{getSortIcon('user__email')}
                  </th>
                  <th
                    className="py-2 pr-4 cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort('grade')}
                  >
                    Класс{getSortIcon('grade')}
                  </th>
                  <th className="py-2 pr-4">Статус</th>
                  <th
                    className="py-2 pr-4 cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort('user__date_joined')}
                  >
                    Дата регистрации{getSortIcon('user__date_joined')}
                  </th>
                  <th className="py-2 pr-4">Действия</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td className="py-4" colSpan={6}>
                      Загрузка...
                    </td>
                  </tr>
                ) : !students || students.length === 0 ? (
                  <tr>
                    <td className="py-4" colSpan={6}>
                      Студенты не найдены
                    </td>
                  </tr>
                ) : (
                  students.map((student) => (
                    <tr key={student.id} className="border-b">
                      <td className="py-2 pr-4">{student.user.full_name}</td>
                      <td className="py-2 pr-4">{student.user.email}</td>
                      <td className="py-2 pr-4">{student.grade || '-'}</td>
                      <td className="py-2 pr-4">
                        <Badge variant={student.user.is_active ? 'default' : 'secondary'}>
                          {student.user.is_active ? 'Активен' : 'Неактивен'}
                        </Badge>
                      </td>
                      <td className="py-2 pr-4">
                        {student.user.date_joined ? new Date(student.user.date_joined).toLocaleDateString('ru-RU') : '-'}
                      </td>
                      <td className="py-2 pr-4">
                        <div className="flex gap-1">
                          <Button type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => setEditUserDialog({ open: true, item: student })}
                            title="Редактировать пользователя"
                          >
                            <UserIcon className="h-4 w-4" />
                          </Button>
                          <Button type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => setSubjectAssignmentDialog({ open: true, item: student })}
                            title="Назначить предметы"
                          >
                            <BookOpen className="h-4 w-4" />
                          </Button>
                          <Button type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => setResetPasswordDialog({ open: true, item: student })}
                            title="Сбросить пароль"
                          >
                            <Key className="h-4 w-4" />
                          </Button>
                          {!student.user.is_active && (
                            <Button type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => setReactivateDialog({ open: true, item: student, isLoading: false })}
                              title="Активировать студента"
                            >
                              <RotateCcw className="h-4 w-4" />
                            </Button>
                          )}
                          <Button type="button"
                            size="sm"
                            variant="destructive"
                            onClick={() => setDeleteUserDialog({ open: true, item: student })}
                            title="Удалить пользователя"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Пагинация */}
          <div className="flex items-center justify-between mt-6 pt-4 border-t">
            <div className="text-sm text-muted-foreground">
              Показано {students?.length || 0} из {totalCount || 0} студентов
            </div>
            <div className="flex gap-2">
              <Button type="button"
                variant="outline"
                size="sm"
                onClick={() => loadStudents(currentPage - 1)}
                disabled={currentPage === 1 || isLoading}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <div className="flex items-center gap-2">
                <span className="text-sm">
                  Страница {currentPage} из {totalPages || 1}
                </span>
              </div>
              <Button type="button"
                variant="outline"
                size="sm"
                onClick={() => loadStudents(currentPage + 1)}
                disabled={currentPage >= totalPages || isLoading}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
    </>
  );

  if (embedded) {
    return (
      <>
        <Card>
          {cardContent}
        </Card>

        {/* Диалог создания студента */}
      <CreateStudentDialog
        open={createDialog}
        onOpenChange={setCreateDialog}
        onSuccess={() => {
          loadStudents(1);
        }}
      />

      {/* Диалог редактирования пользователя */}
      {editUserDialog.item && (
        <EditUserDialog
          user={editUserDialog.item.user}
          profile={editUserDialog.item}
          open={editUserDialog.open}
          onOpenChange={(open) => setEditUserDialog({ open, item: null })}
          onSuccess={() => {
            loadStudents(currentPage);
          }}
        />
      )}

      {/* Диалог сброса пароля */}
      {resetPasswordDialog.item && (
        <ResetPasswordDialog
          user={resetPasswordDialog.item.user}
          open={resetPasswordDialog.open}
          onOpenChange={(open) => setResetPasswordDialog({ open, item: null })}
        />
      )}

      {/* Диалог удаления пользователя */}
      {deleteUserDialog.item && (
        <DeleteUserDialog
          user={deleteUserDialog.item.user}
          open={deleteUserDialog.open}
          onOpenChange={(open) => setDeleteUserDialog({ open, item: null })}
          onSuccess={() => {
            loadStudents(currentPage);
          }}
        />
      )}

      {/* Диалог реактивации пользователя */}
      <Dialog
        open={reactivateDialog.open}
        onOpenChange={(open) => setReactivateDialog({ ...reactivateDialog, open })}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Активировать студента</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-gray-600">
              Вы уверены, что хотите активировать студента <strong>{reactivateDialog.item?.user.full_name}</strong>?
            </p>
          </div>
          <DialogFooter>
            <Button type="button"
              variant="outline"
              onClick={() => setReactivateDialog({ open: false, item: null, isLoading: false })}
              disabled={reactivateDialog.isLoading}
            >
              Отменить
            </Button>
            <Button type="button"
              onClick={handleReactivate}
              disabled={reactivateDialog.isLoading}
            >
              {reactivateDialog.isLoading ? 'Активация...' : 'Активировать'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Диалог назначения предметов */}
      {subjectAssignmentDialog.item && (
        <SubjectAssignmentDialog
          open={subjectAssignmentDialog.open}
          onOpenChange={(open) => setSubjectAssignmentDialog({ open, item: null })}
          studentId={subjectAssignmentDialog.item.id}
          studentName={subjectAssignmentDialog.item.user.full_name}
          onSuccess={() => {
            loadStudents(currentPage);
          }}
        />
      )}
      </>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <Card>
        {cardContent}
      </Card>

      {/* Диалог создания студента */}
      <CreateStudentDialog
        open={createDialog}
        onOpenChange={setCreateDialog}
        onSuccess={() => {
          loadStudents(1);
        }}
      />

      {/* Диалог редактирования пользователя */}
      {editUserDialog.item && (
        <EditUserDialog
          user={editUserDialog.item.user}
          profile={editUserDialog.item}
          open={editUserDialog.open}
          onOpenChange={(open) => setEditUserDialog({ open, item: null })}
          onSuccess={() => {
            loadStudents(currentPage);
          }}
        />
      )}

      {/* Диалог сброса пароля */}
      {resetPasswordDialog.item && (
        <ResetPasswordDialog
          user={resetPasswordDialog.item.user}
          open={resetPasswordDialog.open}
          onOpenChange={(open) => setResetPasswordDialog({ open, item: null })}
        />
      )}

      {/* Диалог удаления пользователя */}
      {deleteUserDialog.item && (
        <DeleteUserDialog
          user={deleteUserDialog.item.user}
          open={deleteUserDialog.open}
          onOpenChange={(open) => setDeleteUserDialog({ open, item: null })}
          onSuccess={() => {
            loadStudents(currentPage);
          }}
        />
      )}

      {/* Диалог реактивации пользователя */}
      <Dialog
        open={reactivateDialog.open}
        onOpenChange={(open) => setReactivateDialog({ ...reactivateDialog, open })}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Активировать студента</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-gray-600">
              Вы уверены, что хотите активировать студента <strong>{reactivateDialog.item?.user.full_name}</strong>?
            </p>
          </div>
          <DialogFooter>
            <Button type="button"
              variant="outline"
              onClick={() => setReactivateDialog({ open: false, item: null, isLoading: false })}
              disabled={reactivateDialog.isLoading}
            >
              Отменить
            </Button>
            <Button type="button"
              onClick={handleReactivate}
              disabled={reactivateDialog.isLoading}
            >
              {reactivateDialog.isLoading ? 'Активация...' : 'Активировать'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Диалог назначения предметов */}
      {subjectAssignmentDialog.item && (
        <SubjectAssignmentDialog
          open={subjectAssignmentDialog.open}
          onOpenChange={(open) => setSubjectAssignmentDialog({ open, item: null })}
          studentId={subjectAssignmentDialog.item.id}
          studentName={subjectAssignmentDialog.item.user.full_name}
          onSuccess={() => {
            loadStudents(currentPage);
          }}
        />
      )}
    </div>
  );
}
