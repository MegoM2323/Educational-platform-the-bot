import { useState } from 'react';
import { User } from '@/integrations/api/unifiedClient';
import { adminAPI } from '@/integrations/api/adminAPI';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

interface DeleteUserDialogProps {
  user: User;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export const DeleteUserDialog = ({ user, open, onOpenChange, onSuccess }: DeleteUserDialogProps) => {
  const [confirmEmail, setConfirmEmail] = useState('');
  const [permanent, setPermanent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async () => {
    setError(null);

    // Проверка подтверждения
    if (confirmEmail.toLowerCase().trim() !== user.email.toLowerCase().trim()) {
      setError('Email не совпадает. Пожалуйста, введите точный email пользователя.');
      return;
    }

    setLoading(true);

    try {
      const response = await adminAPI.deleteUser(user.id, permanent);

      if (response.success) {
        toast.success(permanent ? 'Пользователь удален навсегда' : 'Пользователь деактивирован');
        onSuccess();
        onOpenChange(false);
        // Сброс формы
        setConfirmEmail('');
        setPermanent(false);
      } else {
        setError(response.error || 'Не удалось удалить пользователя');
      }
    } catch (err: any) {
      setError(err?.message || 'Произошла ошибка при удалении пользователя');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setConfirmEmail('');
    setPermanent(false);
    setError(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Удалить пользователя</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {permanent ? (
                <>
                  <strong>ВНИМАНИЕ: Это действие необратимо!</strong>
                  <br />
                  Все данные пользователя <strong>{user.full_name}</strong> будут удалены навсегда из базы данных.
                  Это включает профиль, связанные записи, материалы и историю активности.
                </>
              ) : (
                <>
                  Пользователь <strong>{user.full_name}</strong> будет деактивирован (is_active = False).
                  <br />
                  Вход в систему станет невозможен, но все данные сохранятся и пользователя можно будет восстановить позже.
                </>
              )}
            </AlertDescription>
          </Alert>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="permanent"
              checked={permanent}
              onCheckedChange={(checked) => setPermanent(!!checked)}
              disabled={loading}
            />
            <Label htmlFor="permanent" className="cursor-pointer text-sm font-medium">
              Удалить полностью (hard delete) - НЕОБРАТИМО
            </Label>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmEmail">
              Введите email пользователя для подтверждения:
            </Label>
            <Input
              id="confirmEmail"
              value={confirmEmail}
              onChange={(e) => setConfirmEmail(e.target.value)}
              placeholder={user.email}
              disabled={loading}
              autoComplete="off"
            />
            <p className="text-xs text-muted-foreground">
              Для подтверждения введите: <code className="text-xs bg-muted px-1 py-0.5 rounded">{user.email}</code>
            </p>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Отмена
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={loading || confirmEmail.toLowerCase().trim() !== user.email.toLowerCase().trim()}
          >
            {loading ? 'Удаление...' : permanent ? 'Удалить навсегда' : 'Деактивировать'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
