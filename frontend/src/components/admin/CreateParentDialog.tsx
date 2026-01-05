import { useState } from 'react';
import { adminAPI } from '@/integrations/api/adminAPI';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckCircle, Copy } from 'lucide-react';
import { toast } from 'sonner';

interface CreateParentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

type Step = 'form' | 'success';

interface ParentFormData {
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  password: string;
}

export const CreateParentDialog = ({ open, onOpenChange, onSuccess }: CreateParentDialogProps) => {
  const [step, setStep] = useState<Step>('form');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [credentials, setCredentials] = useState<{ login: string; password: string } | null>(null);

  const [formData, setFormData] = useState<ParentFormData>({
    email: '',
    first_name: '',
    last_name: '',
    phone: '',
    password: '',
  });

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

    setLoading(true);

    try {
      const dataToSend = {
        email: formData.email.trim().toLowerCase(),
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        phone: formData.phone ? formatPhone(formData.phone) : undefined,
        password: formData.password || undefined,
      };

      const response = await adminAPI.createParent(dataToSend);

      if (response.success && response.data) {
        setCredentials(response.data.credentials);
        setStep('success');
        toast.success('Родитель успешно создан');
      } else {
        setError(response.error || 'Не удалось создать родителя');
      }
    } catch (err: any) {
      setError(err?.message || 'Произошла ошибка при создании родителя');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setStep('form');
    setFormData({
      email: '',
      first_name: '',
      last_name: '',
      phone: '',
      password: '',
    });
    setCredentials(null);
    setError(null);
    onOpenChange(false);
  };

  const handleFinish = () => {
    onSuccess();
    handleClose();
  };

  const copyCredentials = () => {
    if (credentials) {
      const text = `Логин: ${credentials.login}\nПароль: ${credentials.password}`;
      navigator.clipboard.writeText(text);
      toast.success('Данные для входа скопированы');
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        {step === 'form' ? (
          <>
            <DialogHeader>
              <DialogTitle>Создать родителя</DialogTitle>
            </DialogHeader>

            <form onSubmit={handleSubmit}>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email *</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                    disabled={loading}
                    placeholder="parent@example.com"
                    autoComplete="username"
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
                      placeholder="Иван"
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
                      placeholder="Иванов"
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
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Пароль (оставьте пустым для автогенерации)</Label>
                  <Input
                    id="password"
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    disabled={loading}
                    placeholder="Автоматический пароль"
                    autoComplete="new-password"
                  />
                  <p className="text-xs text-muted-foreground">
                    Если не указан, будет сгенерирован случайный пароль
                  </p>
                </div>
              </div>

              {error && (
                <Alert variant="destructive" className="mb-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <DialogFooter>
                <Button type="button" variant="outline" onClick={handleClose} disabled={loading}>
                  Отмена
                </Button>
                <Button type="submit" disabled={loading}>
                  {loading ? 'Создание...' : 'Создать'}
                </Button>
              </DialogFooter>
            </form>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Родитель создан!</DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <Alert className="bg-green-50 border-green-200">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-green-800">
                  Родитель успешно создан. Сохраните данные для входа:
                </AlertDescription>
              </Alert>

              {credentials && (
                <div className="bg-muted p-4 rounded-md space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="font-medium">Логин (email):</span>
                    <code className="text-sm">{credentials.login}</code>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-medium">Пароль:</span>
                    <code className="text-sm font-bold">{credentials.password}</code>
                  </div>
                </div>
              )}

              <Button type="button" onClick={copyCredentials} variant="outline" className="w-full">
                <Copy className="h-4 w-4 mr-2" />
                Копировать данные для входа
              </Button>

              <Alert className="bg-yellow-50 border-yellow-200">
                <AlertCircle className="h-4 w-4 text-yellow-600" />
                <AlertDescription className="text-yellow-800 text-sm">
                  Сохраните эти данные! После закрытия окна пароль больше не будет отображаться.
                </AlertDescription>
              </Alert>
            </div>

            <DialogFooter>
              <Button type="button" onClick={handleFinish}>Закрыть</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};
