import { useState, useEffect } from "react";
import { logger } from '@/utils/logger';
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { unifiedAPI as djangoAPI } from "@/integrations/api/unifiedClient";
import { CheckCircle, ArrowLeft, ArrowRight, User, Mail, Phone, MessageCircle, GraduationCap, Target, Users, Trash2, AlertCircle, ChevronDown } from "lucide-react";
import { useErrorNotification, useSuccessNotification, notificationUtils } from "@/components/NotificationSystem";
import { LoadingSpinner, ErrorState } from "@/components/LoadingStates";
import { formatPhoneNumber, getCleanPhone } from "@/utils/validation";

type ApplicantType = 'student' | 'teacher' | 'parent';

interface FormData {
  // Personal Information
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  telegramId: string;
  
  // Application Details
  applicantType: ApplicantType;
  
  // Student-specific fields
  grade: string;
  parentFirstName: string;
  parentLastName: string;
  parentEmail: string;
  parentPhone: string;
  parentTelegramId: string;
  
  // Teacher-specific fields
  subject: string;
  experience: string;
  
  // General fields
  motivation: string;
}

const STORAGE_KEY = "applicationFormData";

export const ApplicationForm = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [includeParentData, setIncludeParentData] = useState(false);
  const [formData, setFormData] = useState<FormData>({
    firstName: "",
    lastName: "",
    email: "",
    phone: "",
    telegramId: "",
    applicantType: "student",
    grade: "",
    parentFirstName: "",
    parentLastName: "",
    parentEmail: "",
    parentPhone: "",
    parentTelegramId: "",
    subject: "",
    experience: "",
    motivation: ""
  });
  const [displayPhone, setDisplayPhone] = useState(""); // Для отображения с форматированием
  const [displayParentPhone, setDisplayParentPhone] = useState(""); // Для отображения с форматированием

  const totalSteps = 3; // Объединили Шаги 3 и 4
  const progress = (currentStep / totalSteps) * 100;

  // Загрузка данных из localStorage при монтировании
  useEffect(() => {
    const savedData = localStorage.getItem(STORAGE_KEY);
    if (savedData) {
      try {
        const parsed = JSON.parse(savedData);
        setFormData(parsed);
        setDisplayPhone(parsed.phone);
        setDisplayParentPhone(parsed.parentPhone);
      } catch (error) {
        logger.error("Ошибка при загрузке сохраненных данных:", error);
      }
    }
  }, []);

  // Сохранение данных в localStorage при изменении
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(formData));
  }, [formData]);

  const validateStep = (step: number): boolean => {
    switch (step) {
      case 1:
        return !!(formData.firstName && formData.lastName && formData.email && formData.phone);
      case 2:
        return !!formData.applicantType;
      case 3:
        // Для студента
        if (formData.applicantType === 'student') {
          // Класс всегда обязателен
          if (!formData.grade) return false;
          // Данные родителя проверяются только если включены
          if (includeParentData) {
            return !!(formData.parentFirstName && formData.parentLastName && formData.parentEmail && formData.parentPhone);
          }
          return true;
        } else if (formData.applicantType === 'teacher') {
          return !!(formData.subject && formData.experience);
        }
        // Родитель - мотивация опциональна
        return true;
      default:
        return false;
    }
  };

  const showError = useErrorNotification();
  const showSuccess = useSuccessNotification();

  const nextStep = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, totalSteps));
      setSubmitError(null); // Очищаем ошибки при переходе к следующему шагу
    } else {
      showError("Пожалуйста, заполните все обязательные поля");
    }
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };

  const handlePhoneChange = (value: string) => {
    // Для отправки на backend отправляем очищенный номер
    const cleanedPhone = getCleanPhone(value);
    setFormData({ ...formData, phone: cleanedPhone });
    // Для отображения форматируем
    setDisplayPhone(value);
  };

  const handleParentPhoneChange = (value: string) => {
    // Для отправки на backend отправляем очищенный номер
    const cleanedPhone = getCleanPhone(value);
    setFormData({ ...formData, parentPhone: cleanedPhone });
    // Для отображения форматируем
    setDisplayParentPhone(value);
  };

  const clearSavedData = () => {
    localStorage.removeItem(STORAGE_KEY);
    setFormData({
      firstName: "",
      lastName: "",
      email: "",
      phone: "",
      telegramId: "",
      applicantType: "student",
      grade: "",
      parentFirstName: "",
      parentLastName: "",
      parentEmail: "",
      parentPhone: "",
      parentTelegramId: "",
      subject: "",
      experience: "",
      motivation: ""
    });
    setDisplayPhone("");
    setDisplayParentPhone("");
    setCurrentStep(1);
    toast.success("Сохраненные данные удалены");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateStep(currentStep)) {
      showError("Пожалуйста, заполните все обязательные поля");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      // Подготавливаем данные для отправки
      let applicationData: any = {
        first_name: formData.firstName,
        last_name: formData.lastName,
        email: formData.email,
        phone: formData.phone,
        telegram_id: formData.telegramId || undefined,
        applicant_type: formData.applicantType,
        grade: formData.grade || undefined,
        subject: formData.subject || undefined,
        experience: formData.experience || undefined,
        motivation: formData.motivation || undefined,
      };

      // Добавляем данные родителя только если они включены для студентов
      if (formData.applicantType === 'student' && includeParentData) {
        applicationData = {
          ...applicationData,
          parent_first_name: formData.parentFirstName || undefined,
          parent_last_name: formData.parentLastName || undefined,
          parent_email: formData.parentEmail || undefined,
          parent_phone: formData.parentPhone || undefined,
          parent_telegram_id: formData.parentTelegramId || undefined,
        };
      } else {
        // Очищаем данные родителя если не указаны
        applicationData = {
          ...applicationData,
          parent_first_name: undefined,
          parent_last_name: undefined,
          parent_email: undefined,
          parent_phone: undefined,
          parent_telegram_id: undefined,
        };
      }

      const response = await djangoAPI.createApplication(applicationData);

      logger.debug("Application submitted:", response);

      // Проверяем успешность ответа
      if (!response.success) {
        throw new Error(response.error || "Ошибка при отправке заявки");
      }

      // Получаем tracking_token перед очисткой
      const trackingToken = response.data?.tracking_token;

      // Показываем уведомление об успехе с отслеживанием
      if (trackingToken) {
        notificationUtils.showApplicationSubmitted(trackingToken);
      } else {
        showSuccess("Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.");
      }

      // Очищаем localStorage при успешной отправке
      localStorage.removeItem(STORAGE_KEY);

      // Reset form
      setFormData({
        firstName: "",
        lastName: "",
        email: "",
        phone: "",
        telegramId: "",
        applicantType: "student",
        grade: "",
        parentFirstName: "",
        parentLastName: "",
        parentEmail: "",
        parentPhone: "",
        parentTelegramId: "",
        subject: "",
        experience: "",
        motivation: ""
      });
      setDisplayPhone("");
      setDisplayParentPhone("");
      setCurrentStep(1);
    } catch (error: any) {
      logger.error("Error submitting application:", error);

      // Определяем тип ошибки и показываем соответствующее сообщение
      let errorMessage = "Произошла ошибка при отправке заявки. Попробуйте еще раз.";

      if (error?.response?.status === 400) {
        errorMessage = "Проверьте правильность заполнения полей";
        // Если backend вернул детальные ошибки полей, выводим их
        if (error?.response?.data?.errors) {
          const fieldErrors = Object.entries(error.response.data.errors)
            .map(([field, messages]: any) => `${field}: ${messages.join(', ')}`)
            .join('\n');
          errorMessage += `\n\n${fieldErrors}`;
        }
      } else if (error?.response?.status === 409) {
        errorMessage = "Заявка с таким email уже существует";
      } else if (error?.response?.status >= 500) {
        errorMessage = "Сервер временно недоступен. Попробуйте позже";
      } else if (error?.message?.includes('network')) {
        errorMessage = "Проблема с подключением к интернету";
      }

      setSubmitError(errorMessage);
      showError(errorMessage, {
        action: {
          label: 'Повторить',
          onClick: () => handleSubmit(e),
        },
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-3">
            <div className="text-center space-y-2">
              <h3 className="text-xl font-semibold">Личная информация</h3>
              <p className="text-muted-foreground text-sm">Заполните основные данные о себе</p>
            </div>

            <div className="flex items-center gap-2 text-xs text-muted-foreground bg-blue-50 dark:bg-blue-950/30 p-3 rounded-lg border border-blue-200/50 dark:border-blue-900/50">
              <AlertCircle className="h-4 w-4 flex-shrink-0 text-blue-600 dark:text-blue-400" />
              <span>Поля отмеченные * обязательны</span>
            </div>

            {/* Имя и фамилия */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <Label htmlFor="firstName" className="text-sm">Имя *</Label>
                </div>
                <Input
                  id="firstName"
                  value={formData.firstName}
                  onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                  placeholder="Иван"
                  required
                  className="max-w-md"
                />
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <Label htmlFor="lastName" className="text-sm">Фамилия *</Label>
                </div>
                <Input
                  id="lastName"
                  value={formData.lastName}
                  onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                  placeholder="Иванов"
                  required
                  className="max-w-md"
                />
              </div>
            </div>

            {/* Email и телефон */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <Label htmlFor="email" className="text-sm">Email *</Label>
                </div>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="example@mail.ru"
                  required
                  className="max-w-md"
                />
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  <Label htmlFor="phone" className="text-sm">Телефон *</Label>
                </div>
                <Input
                  id="phone"
                  type="tel"
                  value={displayPhone}
                  onChange={(e) => handlePhoneChange(e.target.value)}
                  placeholder="+7 (999) 123-45-67"
                  required
                  className="max-w-md"
                />
                <p className="text-xs text-muted-foreground">Формат: +7 (999) 123-45-67</p>
              </div>
            </div>

            {/* Telegram */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <MessageCircle className="h-4 w-4 text-muted-foreground" />
                <Label htmlFor="telegramId" className="text-sm">Telegram ID (необязательно)</Label>
              </div>
              <Input
                id="telegramId"
                value={formData.telegramId}
                onChange={(e) => setFormData({ ...formData, telegramId: e.target.value })}
                placeholder="@username или 123456789"
                className="max-w-md"
              />
              <p className="text-xs text-muted-foreground">Ваш username в Telegram (с @) или числовой ID</p>
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            <div className="text-center space-y-2">
              <h3 className="text-xl font-semibold">Тип заявки</h3>
              <p className="text-muted-foreground">Выберите, кем вы хотите стать на платформе</p>
            </div>

            <RadioGroup
              value={formData.applicantType}
              onValueChange={(value: ApplicantType) => setFormData({ ...formData, applicantType: value })}
              className="space-y-4"
            >
              <div className="flex items-center space-x-3 p-4 border rounded-lg hover:bg-muted/50 cursor-pointer">
                <RadioGroupItem value="student" id="student" />
                <Label htmlFor="student" className="flex items-center space-x-3 cursor-pointer flex-1">
                  <GraduationCap className="h-5 w-5" />
                  <div>
                    <div className="font-medium">Ученик</div>
                    <div className="text-sm text-muted-foreground">Доступ к материалам и общению с учителями</div>
                  </div>
                </Label>
              </div>

              <div className="flex items-center space-x-3 p-4 border rounded-lg hover:bg-muted/50 cursor-pointer">
                <RadioGroupItem value="teacher" id="teacher" />
                <Label htmlFor="teacher" className="flex items-center space-x-3 cursor-pointer flex-1">
                  <User className="h-5 w-5" />
                  <div>
                    <div className="font-medium">Учитель</div>
                    <div className="text-sm text-muted-foreground">Создание материалов и общение с учениками</div>
                  </div>
                </Label>
              </div>

              <div className="flex items-center space-x-3 p-4 border rounded-lg hover:bg-muted/50 cursor-pointer">
                <RadioGroupItem value="parent" id="parent" />
                <Label htmlFor="parent" className="flex items-center space-x-3 cursor-pointer flex-1">
                  <Users className="h-5 w-5" />
                  <div>
                    <div className="font-medium">Родитель</div>
                    <div className="text-sm text-muted-foreground">Контроль успеваемости и оплата обучения</div>
                  </div>
                </Label>
              </div>
            </RadioGroup>
          </div>
        );

      case 3:
        if (formData.applicantType === 'student') {
          return (
            <div className="space-y-3">
              <div className="text-center space-y-2">
                <h3 className="text-xl font-semibold">Дополнительная информация</h3>
                <p className="text-muted-foreground text-sm">Информация об ученике</p>
              </div>

              {/* Информация об ученике */}
              <div className="space-y-3 p-4 border rounded-lg bg-muted/30">
                <div className="flex items-center gap-2">
                  <GraduationCap className="h-4 w-4 text-muted-foreground" />
                  <h4 className="font-medium text-sm text-foreground">Класс *</h4>
                </div>
                <Select value={formData.grade} onValueChange={(value) => setFormData({ ...formData, grade: value })}>
                  <SelectTrigger className="max-w-md">
                    <SelectValue placeholder="Выберите класс" />
                  </SelectTrigger>
                  <SelectContent>
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map((grade) => (
                      <SelectItem key={grade} value={grade.toString()}>
                        {grade} класс
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Данные родителя (Collapsible) */}
              <div className="space-y-0">
                <div className="flex items-center gap-3 p-4 border rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
                  <Checkbox
                    id="includeParent"
                    checked={includeParentData}
                    onCheckedChange={(checked) => setIncludeParentData(checked === true)}
                    className="data-[state=checked]:bg-primary"
                  />
                  <label htmlFor="includeParent" className="flex-1 cursor-pointer flex items-center gap-2">
                    <Users className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <div className="font-medium text-sm">Указать данные родителя (необязательно)</div>
                      <div className="text-xs text-muted-foreground">Добавьте контакты родителя для связи</div>
                    </div>
                  </label>
                  <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${includeParentData ? 'rotate-180' : ''}`} />
                </div>

                {includeParentData && (
                <div className="space-y-3 pl-0">
                  <div className="space-y-3 p-4 border border-t-0 rounded-b-lg bg-muted/20">
                    {/* Имя и фамилия родителя */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4 text-muted-foreground" />
                          <Label htmlFor="parentFirstName" className="text-sm">Имя родителя *</Label>
                        </div>
                        <Input
                          id="parentFirstName"
                          value={formData.parentFirstName}
                          onChange={(e) => setFormData({ ...formData, parentFirstName: e.target.value })}
                          placeholder="Иван"
                          required={includeParentData}
                          className="max-w-md"
                        />
                      </div>
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4 text-muted-foreground" />
                          <Label htmlFor="parentLastName" className="text-sm">Фамилия родителя *</Label>
                        </div>
                        <Input
                          id="parentLastName"
                          value={formData.parentLastName}
                          onChange={(e) => setFormData({ ...formData, parentLastName: e.target.value })}
                          placeholder="Иванов"
                          required={includeParentData}
                          className="max-w-md"
                        />
                      </div>
                    </div>

                    {/* Email и телефон родителя */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Mail className="h-4 w-4 text-muted-foreground" />
                          <Label htmlFor="parentEmail" className="text-sm">Email родителя *</Label>
                        </div>
                        <Input
                          id="parentEmail"
                          type="email"
                          value={formData.parentEmail}
                          onChange={(e) => setFormData({ ...formData, parentEmail: e.target.value })}
                          placeholder="parent@mail.ru"
                          required={includeParentData}
                          className="max-w-md"
                        />
                      </div>
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Phone className="h-4 w-4 text-muted-foreground" />
                          <Label htmlFor="parentPhone" className="text-sm">Телефон родителя *</Label>
                        </div>
                        <Input
                          id="parentPhone"
                          type="tel"
                          value={displayParentPhone}
                          onChange={(e) => handleParentPhoneChange(e.target.value)}
                          placeholder="+7 (999) 123-45-67"
                          required={includeParentData}
                          className="max-w-md"
                        />
                        <p className="text-xs text-muted-foreground">Формат: +7 (999) 123-45-67</p>
                      </div>
                    </div>

                    {/* Telegram родителя */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <MessageCircle className="h-4 w-4 text-muted-foreground" />
                        <Label htmlFor="parentTelegramId" className="text-sm">Telegram ID родителя (необязательно)</Label>
                      </div>
                      <Input
                        id="parentTelegramId"
                        value={formData.parentTelegramId}
                        onChange={(e) => setFormData({ ...formData, parentTelegramId: e.target.value })}
                        placeholder="@username или 123456789"
                        className="max-w-md"
                      />
                      <p className="text-xs text-muted-foreground">Для быстрого контакта</p>
                    </div>
                  </div>
                </div>
                )}
              </div>

              {/* Мотивация */}
              <div className="space-y-3 p-4 border rounded-lg bg-muted/30">
                <div className="flex items-center gap-2">
                  <Target className="h-4 w-4 text-muted-foreground" />
                  <h4 className="font-medium text-sm text-foreground">Ваши цели (необязательно)</h4>
                </div>
                <Textarea
                  id="motivation"
                  value={formData.motivation}
                  onChange={(e) => setFormData({ ...formData, motivation: e.target.value })}
                  placeholder="Какие предметы вас интересуют? Какого результата вы хотите добиться?"
                  rows={3}
                  className="resize-none max-w-2xl"
                />
              </div>
            </div>
          );
        } else if (formData.applicantType === 'teacher') {
          return (
            <div className="space-y-3">
              <div className="text-center space-y-2">
                <h3 className="text-xl font-semibold">Дополнительная информация</h3>
                <p className="text-muted-foreground text-sm">Расскажите о себе как о преподавателе</p>
              </div>

              {/* Предмет */}
              <div className="space-y-3 p-4 border rounded-lg bg-muted/30">
                <div className="flex items-center gap-2">
                  <GraduationCap className="h-4 w-4 text-muted-foreground" />
                  <Label htmlFor="subject" className="font-medium text-sm">Предмет *</Label>
                </div>
                <Select value={formData.subject} onValueChange={(value) => setFormData({ ...formData, subject: value })}>
                  <SelectTrigger className="max-w-md">
                    <SelectValue placeholder="Выберите предмет" />
                  </SelectTrigger>
                  <SelectContent>
                    {['Математика', 'Русский язык', 'Физика', 'Химия', 'Биология', 'История', 'География', 'Английский язык', 'Литература', 'Информатика'].map((subject) => (
                      <SelectItem key={subject} value={subject}>
                        {subject}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Опыт работы */}
              <div className="space-y-3 p-4 border rounded-lg bg-muted/30">
                <div className="flex items-center gap-2">
                  <Target className="h-4 w-4 text-muted-foreground" />
                  <Label htmlFor="experience" className="font-medium text-sm">Опыт работы *</Label>
                </div>
                <Textarea
                  id="experience"
                  value={formData.experience}
                  onChange={(e) => setFormData({ ...formData, experience: e.target.value })}
                  placeholder="Расскажите о своем опыте преподавания, образовании и достижениях"
                  rows={3}
                  required
                  className="resize-none max-w-2xl"
                />
              </div>

              {/* Мотивация */}
              <div className="space-y-3 p-4 border rounded-lg bg-muted/30">
                <div className="flex items-center gap-2">
                  <Target className="h-4 w-4 text-muted-foreground" />
                  <Label htmlFor="motivation" className="font-medium text-sm">Мотивация (необязательно)</Label>
                </div>
                <Textarea
                  id="motivation"
                  value={formData.motivation}
                  onChange={(e) => setFormData({ ...formData, motivation: e.target.value })}
                  placeholder="Почему вы хотите присоединиться? Как вы планируете развиваться на платформе?"
                  rows={3}
                  className="resize-none max-w-2xl"
                />
              </div>
            </div>
          );
        } else if (formData.applicantType === 'parent') {
          return (
            <div className="space-y-3">
              <div className="text-center space-y-2">
                <h3 className="text-xl font-semibold">Дополнительная информация</h3>
                <p className="text-muted-foreground text-sm">Расскажите о своих целях и ожиданиях</p>
              </div>

              {/* Мотивация для родителя */}
              <div className="space-y-3 p-4 border rounded-lg bg-muted/30">
                <div className="flex items-center gap-2">
                  <Target className="h-4 w-4 text-muted-foreground" />
                  <h4 className="font-medium text-sm text-foreground">Ваши цели (необязательно)</h4>
                </div>
                <Textarea
                  id="motivation"
                  value={formData.motivation}
                  onChange={(e) => setFormData({ ...formData, motivation: e.target.value })}
                  placeholder="Какие способности вы хотели бы развивать у ребенка? Какой результат вы ожидаете? Что вас привлекает на нашей платформе?"
                  rows={4}
                  className="resize-none max-w-2xl"
                />
              </div>
            </div>
          );
        }
        return null;

      default:
        return null;
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto">
      <Card className="p-4 md:p-6 lg:p-8 shadow-lg hover:shadow-xl transition-shadow border border-border/50">
        <div className="space-y-4">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-sm">
            <span className="font-medium">Шаг {currentStep} из {totalSteps}</span>
            <span className="text-muted-foreground">{Math.round(progress)}%</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        {/* Error Display */}
        {submitError && (
          <ErrorState
            error={submitError}
            onRetry={() => setSubmitError(null)}
            className="mb-4"
          />
        )}

        {/* Clear saved data button */}
        {localStorage.getItem(STORAGE_KEY) && (
          <div className="flex justify-end">
            <Button type="button"
              variant="ghost"
              size="sm"
              onClick={clearSavedData}
              className="flex items-center space-x-1 text-muted-foreground hover:text-foreground"
            >
              <Trash2 className="h-4 w-4" />
              <span>Очистить сохраненные данные</span>
            </Button>
          </div>
        )}

        {/* Step Content */}
        <form onSubmit={handleSubmit}>
          {renderStepContent()}
        </form>

        {/* Navigation Buttons */}
        <div className="flex justify-between pt-4">
          <Button type="button"
            variant="outline"
            onClick={prevStep}
            disabled={currentStep === 1}
            className="flex items-center space-x-2"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Назад</span>
          </Button>

          {currentStep < totalSteps ? (
            <Button type="button"
              onClick={nextStep}
              disabled={!validateStep(currentStep)}
              className="flex items-center space-x-2"
            >
              <span>Далее</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button type="submit"
              disabled={!validateStep(currentStep) || isSubmitting}
              className="flex items-center space-x-2 gradient-primary shadow-glow hover:opacity-90 transition-opacity"
            >
              {isSubmitting ? (
                <LoadingSpinner size="sm" text="Отправка..." />
              ) : (
                <>
                  <CheckCircle className="h-4 w-4" />
                  <span>Отправить заявку</span>
                </>
              )}
            </Button>
          )}
        </div>
        </div>
      </Card>
    </div>
  );
};
