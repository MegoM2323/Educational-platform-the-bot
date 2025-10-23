import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CreditCard, CheckCircle, Clock, AlertCircle, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";
import { djangoAPI, type Payment } from "@/integrations/django/client";
import { useToast } from "@/hooks/use-toast";

export default function Payments() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [creatingPayment, setCreatingPayment] = useState(false);
  const [paymentForm, setPaymentForm] = useState({
    amount: '12000',
    service_name: 'Расширенный пакет',
    customer_fio: '',
    description: ''
  });
  const { toast } = useToast();

  // Загружаем платежи при монтировании компонента
  useEffect(() => {
    loadPayments();
  }, []);

  const loadPayments = async () => {
    try {
      setLoading(true);
      const paymentsData = await djangoAPI.getPayments();
      setPayments(paymentsData);
    } catch (error) {
      console.error('Ошибка загрузки платежей:', error);
      toast({
        title: "Ошибка",
        description: "Не удалось загрузить платежи",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePayment = async () => {
    if (!paymentForm.customer_fio.trim()) {
      toast({
        title: "Ошибка",
        description: "Введите ФИО плательщика",
        variant: "destructive",
      });
      return;
    }

    try {
      setCreatingPayment(true);
      const payment = await djangoAPI.createPayment({
        amount: paymentForm.amount,
        service_name: paymentForm.service_name,
        customer_fio: paymentForm.customer_fio,
        description: paymentForm.description || `Оплата за ${paymentForm.service_name}`,
        return_url: window.location.origin + '/dashboard/payments'
      });

      if (payment.confirmation_url) {
        // Перенаправляем на страницу оплаты ЮКассы
        window.open(payment.confirmation_url, '_blank');
        toast({
          title: "Платеж создан",
          description: "Откройте новую вкладку для оплаты",
        });
      }
    } catch (error) {
      console.error('Ошибка создания платежа:', error);
      toast({
        title: "Ошибка",
        description: "Не удалось создать платеж",
        variant: "destructive",
      });
    } finally {
      setCreatingPayment(false);
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

      {/* Payment Method */}
      <Card className="p-6">
        <h3 className="text-xl font-bold mb-4">Способ оплаты</h3>
        <div className="space-y-4">
          <div className="p-4 border rounded-lg flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 gradient-primary rounded-lg flex items-center justify-center">
                <CreditCard className="w-6 h-6 text-primary-foreground" />
              </div>
              <div>
                <div className="font-medium">Visa •••• 4242</div>
                <div className="text-sm text-muted-foreground">Срок действия: 12/25</div>
              </div>
            </div>
            <Button variant="outline" size="sm">Изменить</Button>
          </div>
          <Button variant="outline" className="w-full">
            <CreditCard className="w-4 h-4 mr-2" />
            Добавить новый способ оплаты
          </Button>
        </div>
      </Card>

      {/* Payment Form */}
      <Card className="p-6">
        <h3 className="text-xl font-bold mb-4">Оплатить сейчас</h3>
        <div className="space-y-4">
          <div>
            <Label>Сумма (₽)</Label>
            <Input 
              type="number" 
              value={paymentForm.amount}
              onChange={(e) => setPaymentForm(prev => ({ ...prev, amount: e.target.value }))}
              placeholder="12000" 
            />
          </div>
          <div>
            <Label>Услуга</Label>
            <Input 
              value={paymentForm.service_name}
              onChange={(e) => setPaymentForm(prev => ({ ...prev, service_name: e.target.value }))}
              placeholder="Расширенный пакет" 
            />
          </div>
          <div>
            <Label>ФИО плательщика</Label>
            <Input 
              value={paymentForm.customer_fio}
              onChange={(e) => setPaymentForm(prev => ({ ...prev, customer_fio: e.target.value }))}
              placeholder="Иванов Иван Иванович" 
            />
          </div>
          <div>
            <Label>Описание (необязательно)</Label>
            <Input 
              value={paymentForm.description}
              onChange={(e) => setPaymentForm(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Дополнительная информация" 
            />
          </div>
          <Button 
            className="w-full gradient-primary shadow-glow"
            onClick={handleCreatePayment}
            disabled={creatingPayment}
          >
            {creatingPayment ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <CreditCard className="w-4 h-4 mr-2" />
            )}
            {creatingPayment ? 'Создание платежа...' : `Оплатить ${paymentForm.amount}₽`}
          </Button>
        </div>
      </Card>

      {/* Payment History */}
      <Card className="p-6">
        <h3 className="text-xl font-bold mb-4">История платежей</h3>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin mr-2" />
            <span>Загрузка платежей...</span>
          </div>
        ) : payments.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            Платежи не найдены
          </div>
        ) : (
          <div className="space-y-3">
            {payments.map((payment) => (
              <div key={payment.id} className="p-4 border rounded-lg flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    payment.status === "succeeded" ? "bg-success/20" : 
                    payment.status === "pending" ? "bg-accent/20" : "bg-destructive/20"
                  }`}>
                    {payment.status === "succeeded" ? (
                      <CheckCircle className="w-5 h-5 text-success" />
                    ) : payment.status === "pending" ? (
                      <Clock className="w-5 h-5 text-accent" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-destructive" />
                    )}
                  </div>
                  <div>
                    <div className="font-medium">{payment.service_name}</div>
                    <div className="text-sm text-muted-foreground">
                      {new Date(payment.created).toLocaleDateString('ru-RU')}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-bold">{payment.amount}₽</div>
                  <Badge variant={
                    payment.status === "succeeded" ? "default" : 
                    payment.status === "pending" ? "secondary" : "destructive"
                  }>
                    {payment.status === "succeeded" ? "Оплачено" : 
                     payment.status === "pending" ? "Ожидание" : "Отменено"}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Available Plans */}
      <div>
        <h3 className="text-xl font-bold mb-4">Доступные тарифы</h3>
        <div className="grid md:grid-cols-3 gap-4">
          {plans.map((plan, index) => (
            <Card key={index} className={`p-6 ${plan.popular ? "border-primary shadow-lg" : ""}`}>
              {plan.popular && (
                <Badge className="mb-4">Популярный</Badge>
              )}
              <h4 className="text-xl font-bold mb-2">{plan.name}</h4>
              <div className="text-3xl font-bold mb-4">{plan.price}₽<span className="text-sm font-normal text-muted-foreground">/мес</span></div>
              <ul className="space-y-2 mb-6">
                {plan.features.map((feature, idx) => (
                  <li key={idx} className="flex items-center gap-2 text-sm">
                    <CheckCircle className="w-4 h-4 text-success" />
                    {feature}
                  </li>
                ))}
              </ul>
              <Button 
                className={plan.popular ? "w-full gradient-primary shadow-glow" : "w-full"}
                variant={plan.popular ? "default" : "outline"}
              >
                Выбрать план
              </Button>
            </Card>
          ))}
        </div>
      </div>
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
