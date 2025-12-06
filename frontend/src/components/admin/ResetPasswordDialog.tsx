import { useState } from 'react';
import { User } from '@/integrations/api/unifiedClient';
import { adminAPI } from '@/integrations/api/adminAPI';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Copy, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';

interface ResetPasswordDialogProps {
  user: User;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const ResetPasswordDialog = ({ user, open, onOpenChange }: ResetPasswordDialogProps) => {
  const [newPassword, setNewPassword] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleReset = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await adminAPI.resetPassword(user.id);

      if (response.success && response.data) {
        setNewPassword(response.data.new_password);
        toast.success('Пароль успешно сброшен');
      } else {
        setError(response.error || 'Не удалось сбросить пароль');
      }
    } catch (err: any) {
      setError(err?.message || 'Произошла ошибка при сбросе пароля');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (newPassword) {
      navigator.clipboard.writeText(newPassword);
      toast.success('Пароль скопирован в буфер обмена');
    }
  };

  const handleClose = () => {
    setNewPassword(null);
    setError(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Сбросить пароль</DialogTitle>
        </DialogHeader>

        {!newPassword ? (
          <>
            <div className="py-4 space-y-4">
              <p>
                Вы уверены, что хотите сбросить пароль для пользователя{' '}
                <strong>{user.full_name}</strong> ({user.email})?
              </p>
              <p className="text-sm text-muted-foreground">
                Будет сгенерирован новый случайный пароль. Текущий пароль пользователя перестанет работать.
              </p>
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleClose} disabled={loading}>
                Отмена
              </Button>
              <Button type="button" onClick={handleReset} disabled={loading}>
                {loading ? 'Генерация...' : 'Сбросить пароль'}
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <Alert className="bg-yellow-50 border-yellow-200">
              <AlertCircle className="h-4 w-4 text-yellow-600" />
              <AlertDescription className="text-yellow-800">
                Новый пароль сгенерирован. <strong>Сохраните его</strong>, он показывается только один раз!
              </AlertDescription>
            </Alert>

            <div className="space-y-4 py-4">
              <div>
                <p className="text-sm font-medium mb-2">Новый пароль:</p>
                <div className="bg-muted p-4 rounded-md flex items-center justify-between">
                  <code className="text-lg font-mono font-bold">{newPassword}</code>
                  <Button type="button" size="sm" variant="outline" onClick={copyToClipboard}>
                    <Copy className="h-4 w-4 mr-1" />
                    Копировать
                  </Button>
                </div>
              </div>

              <div className="bg-green-50 border border-green-200 p-3 rounded-md flex items-start gap-2">
                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-green-800">
                  <p className="font-medium">Пароль успешно сброшен</p>
                  <p className="mt-1">
                    Отправьте этот пароль пользователю {user.full_name}. После закрытия этого окна пароль
                    больше не будет отображаться.
                  </p>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" onClick={handleClose}>Закрыть</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};
