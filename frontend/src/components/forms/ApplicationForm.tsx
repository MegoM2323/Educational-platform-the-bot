import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { unifiedAPI as djangoAPI } from "@/integrations/api/unifiedClient";
import { CheckCircle, ArrowLeft, ArrowRight, User, GraduationCap, Users } from "lucide-react";
import { useErrorNotification, useSuccessNotification, notificationUtils } from "@/components/NotificationSystem";
import { LoadingSpinner, ErrorState } from "@/components/LoadingStates";

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

export const ApplicationForm = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
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

  const totalSteps = 4;
  const progress = (currentStep / totalSteps) * 100;

  const validateStep = (step: number): boolean => {
    switch (step) {
      case 1:
        return !!(formData.firstName && formData.lastName && formData.email && formData.phone);
      case 2:
        return formData.applicantType !== '';
      case 3:
        if (formData.applicantType === 'student') {
          return !!(formData.grade && formData.parentFirstName && formData.parentLastName && formData.parentEmail && formData.parentPhone);
        } else if (formData.applicantType === 'teacher') {
          return !!(formData.subject && formData.experience);
        }
        return true;
      case 4:
        return !!formData.motivation;
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
      const applicationData = {
        first_name: formData.firstName,
        last_name: formData.lastName,
        email: formData.email,
        phone: formData.phone,
        telegram_id: formData.telegramId || undefined,
        applicant_type: formData.applicantType,
        grade: formData.grade || undefined,
        subject: formData.subject || undefined,
        experience: formData.experience || undefined,
        motivation: formData.motivation,
        parent_first_name: formData.parentFirstName || undefined,
        parent_last_name: formData.parentLastName || undefined,
        parent_email: formData.parentEmail || undefined,
        parent_phone: formData.parentPhone || undefined,
        parent_telegram_id: formData.parentTelegramId || undefined,
      };

      const response = await djangoAPI.createApplication(applicationData);
      
      console.log("Application submitted:", response);
      
      // Показываем уведомление об успехе с отслеживанием
      if (response.tracking_token) {
        notificationUtils.showApplicationSubmitted(response.tracking_token);
      } else {
        showSuccess("Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.");
      }
      
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
      setCurrentStep(1);
    } catch (error: any) {
      console.error("Error submitting application:", error);
      
      // Определяем тип ошибки и показываем соответствующее сообщение
      let errorMessage = "Произошла ошибка при отправке заявки. Попробуйте еще раз.";
      
      if (error?.response?.status === 400) {
        errorMessage = "Проверьте правильность заполнения полей";
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
          <div className="space-y-6">
            <div className="text-center space-y-2">
              <h3 className="text-xl font-semibold">Личная информация</h3>
              <p className="text-muted-foreground">Заполните основные данные о себе</p>
            </div>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="firstName">Имя *</Label>
                <Input
                  id="firstName"
                  value={formData.firstName}
                  onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                  placeholder="Иван"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="lastName">Фамилия *</Label>
                <Input
                  id="lastName"
                  value={formData.lastName}
                  onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                  placeholder="Иванов"
                  required
                />
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email *</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="example@mail.ru"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="phone">Телефон *</Label>
                <Input
                  id="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="+7 (999) 123-45-67"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="telegramId">Telegram ID (необязательно)</Label>
              <Input
                id="telegramId"
                value={formData.telegramId}
                onChange={(e) => setFormData({ ...formData, telegramId: e.target.value })}
                placeholder="@username или ID"
              />
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
            <div className="space-y-6">
              <div className="text-center space-y-2">
                <h3 className="text-xl font-semibold">Информация об ученике</h3>
                <p className="text-muted-foreground">Дополнительные данные для ученика</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="grade">Класс *</Label>
                <Select value={formData.grade} onValueChange={(value) => setFormData({ ...formData, grade: value })}>
                  <SelectTrigger>
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

              <div className="space-y-4">
                <div className="text-lg font-medium">Информация о родителе</div>
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="parentFirstName">Имя родителя *</Label>
                    <Input
                      id="parentFirstName"
                      value={formData.parentFirstName}
                      onChange={(e) => setFormData({ ...formData, parentFirstName: e.target.value })}
                      placeholder="Иван"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="parentLastName">Фамилия родителя *</Label>
                    <Input
                      id="parentLastName"
                      value={formData.parentLastName}
                      onChange={(e) => setFormData({ ...formData, parentLastName: e.target.value })}
                      placeholder="Иванов"
                      required
                    />
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="parentEmail">Email родителя *</Label>
                    <Input
                      id="parentEmail"
                      type="email"
                      value={formData.parentEmail}
                      onChange={(e) => setFormData({ ...formData, parentEmail: e.target.value })}
                      placeholder="parent@mail.ru"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="parentPhone">Телефон родителя *</Label>
                    <Input
                      id="parentPhone"
                      type="tel"
                      value={formData.parentPhone}
                      onChange={(e) => setFormData({ ...formData, parentPhone: e.target.value })}
                      placeholder="+7 (999) 123-45-67"
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="parentTelegramId">Telegram ID родителя (необязательно)</Label>
                  <Input
                    id="parentTelegramId"
                    value={formData.parentTelegramId}
                    onChange={(e) => setFormData({ ...formData, parentTelegramId: e.target.value })}
                    placeholder="@username или ID"
                  />
                </div>
              </div>
            </div>
          );
        } else if (formData.applicantType === 'teacher') {
          return (
            <div className="space-y-6">
              <div className="text-center space-y-2">
                <h3 className="text-xl font-semibold">Информация об учителе</h3>
                <p className="text-muted-foreground">Дополнительные данные для учителя</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="subject">Предмет *</Label>
                <Input
                  id="subject"
                  value={formData.subject}
                  onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                  placeholder="Математика, Физика, Химия..."
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="experience">Опыт работы *</Label>
                <Textarea
                  id="experience"
                  value={formData.experience}
                  onChange={(e) => setFormData({ ...formData, experience: e.target.value })}
                  placeholder="Расскажите о своем опыте преподавания, образовании и достижениях"
                  rows={4}
                  required
                />
              </div>
            </div>
          );
        }
        return null;

      case 4:
        return (
          <div className="space-y-6">
            <div className="text-center space-y-2">
              <h3 className="text-xl font-semibold">Мотивация</h3>
              <p className="text-muted-foreground">Расскажите, почему вы хотите присоединиться к платформе</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="motivation">Мотивация *</Label>
              <Textarea
                id="motivation"
                value={formData.motivation}
                onChange={(e) => setFormData({ ...formData, motivation: e.target.value })}
                placeholder="Расскажите о своих целях, ожиданиях и том, как вы планируете использовать платформу"
                rows={6}
                required
              />
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Card className="p-6 md:p-8">
      <div className="space-y-6">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>Шаг {currentStep} из {totalSteps}</span>
            <span>{Math.round(progress)}%</span>
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

        {/* Step Content */}
        <form onSubmit={handleSubmit}>
          {renderStepContent()}
        </form>

        {/* Navigation Buttons */}
        <div className="flex justify-between">
          <Button
            type="button"
            variant="outline"
            onClick={prevStep}
            disabled={currentStep === 1}
            className="flex items-center space-x-2"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Назад</span>
          </Button>

          {currentStep < totalSteps ? (
            <Button
              type="button"
              onClick={nextStep}
              disabled={!validateStep(currentStep)}
              className="flex items-center space-x-2"
            >
              <span>Далее</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="submit"
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
  );
};
