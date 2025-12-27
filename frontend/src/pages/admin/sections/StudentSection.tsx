import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Plus, Search, User, Key, Trash2, BookOpen } from 'lucide-react';
import { adminAPI } from '@/integrations/api/adminAPI';
import { toast } from 'sonner';
import { CreateStudentDialog } from '@/components/admin/CreateStudentDialog';
import { EditUserDialog } from '@/components/admin/EditUserDialog';
import { ResetPasswordDialog } from '@/components/admin/ResetPasswordDialog';
import { DeleteUserDialog } from '@/components/admin/DeleteUserDialog';
import { SubjectAssignmentDialog } from '@/components/admin/SubjectAssignmentDialog';
import { User as UserType } from '@/integrations/api/unifiedClient';

interface StudentItem {
  id: number;
  user: UserType;
  grade?: string;
  tutor_id?: number | null;
  parent_id?: number | null;
}

interface StudentSectionProps {
  onUpdate?: () => void;
}

export default function StudentSection({ onUpdate }: StudentSectionProps) {
  const [students, setStudents] = useState<StudentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [createDialog, setCreateDialog] = useState(false);

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
  const [subjectAssignmentDialog, setSubjectAssignmentDialog] = useState<{
    open: boolean;
    item: StudentItem | null;
  }>({ open: false, item: null });

  useEffect(() => {
    loadStudents();
  }, []);

  const loadStudents = async () => {
    setIsLoading(true);
    try {
      const response = await adminAPI.getStudents({ page_size: 5, search: searchTerm });
      if (response.success && response.data) {
        setStudents(response.data.results || []);
      } else {
        toast.error(response.error || 'Ошибка загрузки студентов');
      }
    } catch (error) {
      toast.error('Ошибка загрузки студентов');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = () => {
    loadStudents();
  };

  const handleSuccess = () => {
    loadStudents();
    onUpdate?.();
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Студенты</CardTitle>
            <Button type="button" size="sm" onClick={() => setCreateDialog(true)}>
              <Plus className="h-4 w-4 mr-1" />
              Создать
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Поиск */}
          <div className="flex gap-2">
            <Input
              placeholder="Поиск по ФИО, email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="flex-1"
            />
            <Button type="button" variant="outline" size="icon" onClick={handleSearch}>
              <Search className="h-4 w-4" />
            </Button>
          </div>

          {/* Список студентов */}
          <div className="space-y-2">
            {isLoading ? (
              <div className="text-sm text-muted-foreground text-center py-4">Загрузка...</div>
            ) : students.length === 0 ? (
              <div className="text-sm text-muted-foreground text-center py-4">
                Студенты не найдены
              </div>
            ) : (
              students.map((student) => (
                <div
                  key={student.id}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50"
                >
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{student.user.full_name}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {student.user.email}
                    </div>
                    <div className="flex gap-1 mt-1">
                      {student.grade && (
                        <Badge variant="outline" className="text-xs">
                          {student.grade} класс
                        </Badge>
                      )}
                      <Badge variant={student.user.is_active ? 'default' : 'secondary'} className="text-xs">
                        {student.user.is_active ? 'Активен' : 'Неактивен'}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex gap-1 ml-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setEditUserDialog({ open: true, item: student })}
                      title="Редактировать"
                    >
                      <User className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setSubjectAssignmentDialog({ open: true, item: student })}
                      title="Предметы"
                    >
                      <BookOpen className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setResetPasswordDialog({ open: true, item: student })}
                      title="Сбросить пароль"
                    >
                      <Key className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setDeleteUserDialog({ open: true, item: student })}
                      title="Удалить"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Диалоги */}
      <CreateStudentDialog
        open={createDialog}
        onOpenChange={setCreateDialog}
        onSuccess={handleSuccess}
      />

      {editUserDialog.item && (
        <EditUserDialog
          user={editUserDialog.item.user}
          profile={editUserDialog.item}
          open={editUserDialog.open}
          onOpenChange={(open) => setEditUserDialog({ open, item: null })}
          onSuccess={handleSuccess}
        />
      )}

      {resetPasswordDialog.item && (
        <ResetPasswordDialog
          user={resetPasswordDialog.item.user}
          open={resetPasswordDialog.open}
          onOpenChange={(open) => setResetPasswordDialog({ open, item: null })}
        />
      )}

      {deleteUserDialog.item && (
        <DeleteUserDialog
          user={deleteUserDialog.item.user}
          open={deleteUserDialog.open}
          onOpenChange={(open) => setDeleteUserDialog({ open, item: null })}
          onSuccess={handleSuccess}
        />
      )}

      {subjectAssignmentDialog.item && (
        <SubjectAssignmentDialog
          open={subjectAssignmentDialog.open}
          onOpenChange={(open) => setSubjectAssignmentDialog({ open, item: null })}
          studentId={subjectAssignmentDialog.item.id}
          studentName={subjectAssignmentDialog.item.user.full_name}
          onSuccess={handleSuccess}
        />
      )}
    </>
  );
}
