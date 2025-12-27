import { useState, useEffect } from 'react';
import { User } from '@/integrations/api/unifiedClient';
import { adminAPI } from '@/integrations/api/adminAPI';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { StaffListItem } from '@/services/staffService';

interface EditTutorDialogProps {
  tutor: StaffListItem;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export const EditTutorDialog = ({ tutor, open, onOpenChange, onSuccess }: EditTutorDialogProps) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    first_name: tutor.user.first_name || '',
    last_name: tutor.user.last_name || '',
    email: tutor.user.email || '',
    phone: tutor.user.phone || '',
    is_active: tutor.user.is_active !== false,
    specialization: tutor.specialization || '',
    experience_years: tutor.experience_years || 0,
    bio: tutor.bio || '',
  });

  useEffect(() => {
    if (open && tutor) {
      setFormData({
        first_name: tutor.user.first_name || '',
        last_name: tutor.user.last_name || '',
        email: tutor.user.email || '',
        phone: tutor.user.phone || '',
        is_active: tutor.user.is_active !== false,
        specialization: tutor.specialization || '',
        experience_years: tutor.experience_years || 0,
        bio: tutor.bio || '',
      });
      setError(null);
    }
  }, [open, tutor]);

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

    if (!formData.specialization) {
      setError('Специализация обязательна для тьютора');
      return;
    }

    setLoading(true);

    try {
      const dataToSend = {
        email: formData.email.trim().toLowerCase(),
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        phone: formData.phone ? formatPhone(formData.phone) : undefined,
        is_active: formData.is_active,
        specialization: formData.specialization.trim(),
        experience_years: formData.experience_years,
        bio: formData.bio || undefined,
      };

      const response = await adminAPI.editTutor(tutor.id, dataToSend);

      if (response.success) {
        toast.success('Тьютор успешно обновлен');
        onSuccess();
        onOpenChange(false);
      } else {
        setError(response.error || 'Ошибка обновления тьютора');
      }
    } catch (err: any) {
      setError(err?.message || 'Произошла ошибка при обновлении тьютора');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Редактировать тьютора</DialogTitle>
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

            <div className="border-t pt-4 mt-4">
              <h3 className="text-sm font-medium mb-3">Профиль тьютора</h3>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="specialization">Специализация *</Label>
                  <Input
                    id="specialization"
                    value={formData.specialization}
                    onChange={(e) => setFormData({ ...formData, specialization: e.target.value })}
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
                    value={formData.experience_years}
                    onChange={(e) =>
                      setFormData({ ...formData, experience_years: parseInt(e.target.value) || 0 })
                    }
                    disabled={loading}
                    min="0"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="bio">Биография</Label>
                  <Textarea
                    id="bio"
                    value={formData.bio}
                    onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                    disabled={loading}
                    placeholder="Расскажите о тьюторе"
                    rows={4}
                  />
                </div>
              </div>
            </div>
          </div>

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
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
