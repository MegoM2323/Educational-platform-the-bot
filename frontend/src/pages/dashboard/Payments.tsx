import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CreditCard, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { apiClient } from "@/integrations/api/migration";
import { useToast } from "@/hooks/use-toast";

interface ChildSubject {
  id: number;
  name: string;
  teacher_name: string;
  enrollment_status: 'active' | 'inactive';
  payment_status: 'paid' | 'pending' | 'overdue' | 'no_payment';
}

interface ChildItem {
  id: number;
  full_name: string;
  email: string;
  grade: string;
  goal: string;
  subjects: ChildSubject[];
}

export default function Payments() {
  const { toast } = useToast();
  const [children, setChildren] = useState<ChildItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [creatingFor, setCreatingFor] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const resp = await apiClient.request<ChildItem[]>(`/materials/dashboard/parent/children/`);
        if (resp.data) {
          setChildren(resp.data);
        } else {
          throw new Error(resp.error || 'Не удалось загрузить данные');
        }
      } catch (e) {
        toast({
          title: 'Ошибка',
          description: 'Не удалось загрузить список предметов детей',
          variant: 'destructive',
        });
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const initiatePayment = async (childId: number, subjectId: number) => {
    try {
      setCreatingFor(`${childId}:${subjectId}`);
      const resp = await apiClient.request<{ payment_url?: string }>(`/materials/dashboard/parent/children/${childId}/payment/${subjectId}/`, {
        method: 'POST',
        body: JSON.stringify({ amount: 5000.0, description: 'Оплата за предмет за месяц обучения' }),
      });
      if (resp.data?.payment_url) {
        window.location.href = resp.data.payment_url;
      } else {
        throw new Error(resp.error || 'Не удалось создать платеж');
      }
    } catch (e) {
      toast({
        title: 'Ошибка',
        description: 'Не удалось создать платеж',
        variant: 'destructive',
      });
    } finally {
      setCreatingFor(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Оплата услуг</h1>
        <p className="text-muted-foreground">Управляйте подпиской и платежами</p>
      </div>

      {/* Current Plan */}
      <Card className="p-6 gradient-primary text-primary-foreground shadow-glow">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-2xl font-bold mb-2">Текущий тариф</h3>
            <p className="text-primary-foreground/80">Расширенный пакет</p>
          </div>
          <Badge className="bg-primary-foreground/20 text-primary-foreground hover:bg-primary-foreground/30">
            Активен
          </Badge>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-3xl font-bold">8</div>
            <div className="text-sm text-primary-foreground/80">занятий в месяц</div>
          </div>
          <div>
            <div className="text-3xl font-bold">3</div>
            <div className="text-sm text-primary-foreground/80">предмета</div>
          </div>
          <div>
            <div className="text-3xl font-bold">15</div>
            <div className="text-sm text-primary-foreground/80">дней до оплаты</div>
          </div>
          <div>
            <div className="text-3xl font-bold">12,000₽</div>
            <div className="text-sm text-primary-foreground/80">в месяц</div>
          </div>
        </div>
      </Card>

      {/* Оплата по предметам детей (фиксированная 5000₽) */}
      <Card className="p-6">
        <h3 className="text-xl font-bold mb-4">Оплата предметов детей</h3>
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" /> Загрузка...
          </div>
        ) : (
          <div className="space-y-4">
            {children.map((child) => (
              <div key={child.id} className="space-y-2">
                <div className="font-medium">{child.full_name}</div>
                <div className="space-y-2">
                  {child.subjects.map((subject) => (
                    <div key={subject.id} className="flex items-center justify-between p-2 border rounded">
                      <div>
                        <div className="text-sm font-medium">{subject.name}</div>
                        <div className="text-xs text-muted-foreground">{subject.teacher_name}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={
                          subject.payment_status === 'paid' ? 'default' :
                          subject.payment_status === 'overdue' ? 'destructive' :
                          subject.payment_status === 'pending' ? 'secondary' : 'outline'
                        }>
                          {subject.payment_status === 'paid' ? 'Оплачено' :
                           subject.payment_status === 'overdue' ? 'Просрочено' :
                           subject.payment_status === 'pending' ? 'Ожидание' : 'Нет платежа'}
                        </Badge>
                        <Button
                          size="sm"
                          onClick={() => initiatePayment(child.id, subject.id)}
                          disabled={creatingFor === `${child.id}:${subject.id}`}
                        >
                          {creatingFor === `${child.id}:${subject.id}` ? (
                            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                          ) : (
                            <CreditCard className="w-3 h-3 mr-1" />
                          )}
                          Оплатить 5000₽
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            {children.length === 0 && (
              <div className="text-sm text-muted-foreground">Нет зарегистрированных детей</div>
            )}
          </div>
        )}
      </Card>

      {/* Подсказка */}
      <Card className="p-6">
        <div className="text-sm text-muted-foreground">
          После успешной оплаты вы автоматически вернётесь в систему.
        </div>
      </Card>

      {/* Удалены маркетинговые тарифы для упрощения UX оплаты по предметам */}
    </div>
  );
}


const plans = [
  {
    name: "Базовый",
    price: "8,000",
    features: [
      "4 занятия в месяц",
      "1 предмет",
      "Доступ к материалам",
      "Чат с преподавателем"
    ],
    popular: false
  },
  {
    name: "Расширенный",
    price: "12,000",
    features: [
      "8 занятий в месяц",
      "3 предмета",
      "Доступ к материалам",
      "Чат с преподавателем",
      "Личный тьютор"
    ],
    popular: true
  },
  {
    name: "Премиум",
    price: "20,000",
    features: [
      "12 занятий в месяц",
      "Все предметы",
      "Доступ к материалам",
      "Чат с преподавателем",
      "Личный тьютор",
      "Индивидуальный план"
    ],
    popular: false
  }
];
