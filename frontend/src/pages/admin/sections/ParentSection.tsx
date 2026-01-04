import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Plus, Search, User, Key, Trash2, Link2 } from 'lucide-react';
import { adminAPI } from '@/integrations/api/adminAPI';
import { toast } from 'sonner';
import { CreateParentDialog } from '@/components/admin/CreateParentDialog';
import { EditUserDialog } from '@/components/admin/EditUserDialog';
import { ResetPasswordDialog } from '@/components/admin/ResetPasswordDialog';
import { DeleteUserDialog } from '@/components/admin/DeleteUserDialog';
import { ConfirmDeleteDialog } from '@/components/admin/ConfirmDeleteDialog';
import { ParentStudentAssignment } from '@/components/admin/ParentStudentAssignment';
import { User as UserType } from '@/integrations/api/unifiedClient';

interface ParentItem {
  id: number;
  user: UserType;
  children_count?: number;
}

interface ParentSectionProps {
  onUpdate?: () => void;
}

export default function ParentSection({ onUpdate }: ParentSectionProps) {
  const [parents, setParents] = useState<ParentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [createDialog, setCreateDialog] = useState(false);
  const [assignmentDialog, setAssignmentDialog] = useState(false);

  // Диалоги
  const [editUserDialog, setEditUserDialog] = useState<{
    open: boolean;
    item: ParentItem | null;
  }>({ open: false, item: null });
  const [resetPasswordDialog, setResetPasswordDialog] = useState<{
    open: boolean;
    item: ParentItem | null;
  }>({ open: false, item: null });
  const [confirmDeleteDialog, setConfirmDeleteDialog] = useState<{
    open: boolean;
    item: ParentItem | null;
  }>({ open: false, item: null });
  const [deleteUserDialog, setDeleteUserDialog] = useState<{
    open: boolean;
    item: ParentItem | null;
  }>({ open: false, item: null });

  useEffect(() => {
    loadParents();
  }, []);

  const loadParents = async () => {
    setIsLoading(true);
    try {
      const response = await adminAPI.listParents();
      if (response.success && response.data) {
        const parentsList = response.data.results || [];
        // Применяем фильтр по поисковому запросу
        if (searchTerm) {
          const filtered = parentsList.filter(
            (p: ParentItem) =>
              (p.user.full_name?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
              (p.user.email?.toLowerCase() || '').includes(searchTerm.toLowerCase())
          );
          setParents(filtered.slice(0, 5));
        } else {
          setParents(parentsList.slice(0, 5));
        }
      } else {
        toast.error(response.error || 'Ошибка загрузки родителей');
      }
    } catch (error) {
      toast.error('Ошибка загрузки родителей');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = () => {
    loadParents();
  };

  const handleSuccess = () => {
    loadParents();
    onUpdate?.();
  };

  const handleConfirmDelete = () => {
    if (confirmDeleteDialog.item) {
      setConfirmDeleteDialog({ open: false, item: null });
      setDeleteUserDialog({ open: true, item: confirmDeleteDialog.item });
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Родители</CardTitle>
            <div className="flex gap-2">
              <Button type="button" size="sm" variant="outline" onClick={() => setAssignmentDialog(true)}>
                <Link2 className="h-4 w-4 mr-1" />
                Привязать
              </Button>
              <Button type="button" size="sm" onClick={() => setCreateDialog(true)}>
                <Plus className="h-4 w-4 mr-1" />
                Создать
              </Button>
            </div>
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

          {/* Список родителей */}
          <div className="space-y-2">
            {isLoading ? (
              <div className="text-sm text-muted-foreground text-center py-4">Загрузка...</div>
            ) : parents.length === 0 ? (
              <div className="text-sm text-muted-foreground text-center py-4">
                Родители не найдены
              </div>
            ) : (
              parents.map((parent) => (
                <div
                  key={parent.id}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50"
                >
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{parent.user.full_name}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {parent.user.email}
                    </div>
                    <div className="flex gap-1 mt-1">
                      {parent.children_count !== undefined && (
                        <Badge variant="secondary" className="text-xs">
                          {parent.children_count} {parent.children_count === 1 ? 'ребенок' : 'детей'}
                        </Badge>
                      )}
                      <Badge variant={parent.user.is_active ? 'default' : 'secondary'} className="text-xs">
                        {parent.user.is_active ? 'Активен' : 'Неактивен'}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex gap-1 ml-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setEditUserDialog({ open: true, item: parent })}
                      title="Редактировать"
                    >
                      <User className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setResetPasswordDialog({ open: true, item: parent })}
                      title="Сбросить пароль"
                    >
                      <Key className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setConfirmDeleteDialog({ open: true, item: parent })}
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
      <CreateParentDialog
        open={createDialog}
        onOpenChange={setCreateDialog}
        onSuccess={handleSuccess}
      />

      <ParentStudentAssignment
        open={assignmentDialog}
        onOpenChange={setAssignmentDialog}
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

      {confirmDeleteDialog.item && (
        <ConfirmDeleteDialog
          open={confirmDeleteDialog.open}
          onOpenChange={(open) => setConfirmDeleteDialog({ open, item: null })}
          onConfirm={handleConfirmDelete}
          userName={confirmDeleteDialog.item.user.full_name}
          title="Delete Parent?"
          description="Are you sure you want to delete this parent? This action will deactivate the parent account."
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
    </>
  );
}
