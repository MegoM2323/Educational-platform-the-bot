import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { BookOpen, ArrowLeft } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { validateEmail, validateName, validatePhone } from "@/utils/validation";
import { ValidationMessage } from "@/components/ValidationMessage";
import { safeJsonParse } from "../utils/jsonUtils";
import { unifiedAPI as djangoAPI } from "@/integrations/api/unifiedClient";

interface ApplicationData {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  telegram_id: string;
  applicant_type: string;
  grade: string;
  subject: string;
  experience: string;
  motivation: string;
  parent_first_name: string;
  parent_last_name: string;
  parent_email: string;
  parent_phone: string;
  parent_telegram_id: string;
}

const ApplicationForm = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [applicationData, setApplicationData] = useState<ApplicationData>({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    telegram_id: "",
    applicant_type: "",
    grade: "",
    subject: "",
    experience: "",
    motivation: "",
    parent_first_name: "",
    parent_last_name: "",
    parent_email: "",
    parent_phone: "",
    parent_telegram_id: ""
  });

  const totalSteps = 3;

  const handleInputChange = (field: keyof ApplicationData, value: string) => {
    setApplicationData(prev => ({ ...prev, [field]: value }));
  };

  const validateStep1 = () => {
    if (!applicationData.first_name.trim()) {
      toast.error("Пожалуйста, введите имя");
      return false;
    }
    if (!applicationData.last_name.trim()) {
      toast.error("Пожалуйста, введите фамилию");
      return false;
    }
    if (!validateEmail(applicationData.email)) {
      toast.error("Пожалуйста, введите корректный email");
      return false;
    }
    const phoneValidation = validatePhone(applicationData.phone);
    if (!phoneValidation.isValid) {
      toast.error(phoneValidation.message!);
      return false;
    }
    if (!applicationData.applicant_type) {
      toast.error("Пожалуйста, выберите тип заявки");
      return false;
    }
    return true;
  };

  const validateStep2 = () => {
    if (applicationData.applicant_type === "student") {
      if (!applicationData.grade.trim()) {
        toast.error("Пожалуйста, укажите класс");
        return false;
      }
      if (!applicationData.motivation.trim()) {
        toast.error("Пожалуйста, укажите цель обучения");
        return false;
      }
    } else if (applicationData.applicant_type === "teacher") {
      if (!applicationData.subject.trim()) {
        toast.error("Пожалуйста, укажите предмет");
        return false;
      }
      if (!applicationData.experience.trim()) {
        toast.error("Пожалуйста, укажите опыт работы");
        return false;
      }
    }
    return true;
  };

  const validateStep3 = () => {
    if (applicationData.applicant_type === "student") {
      if (!applicationData.parent_first_name.trim()) {
        toast.error("Пожалуйста, введите имя родителя");
        return false;
      }
      if (!applicationData.parent_last_name.trim()) {
        toast.error("Пожалуйста, введите фамилию родителя");
        return false;
      }
      if (!validateEmail(applicationData.parent_email)) {
        toast.error("Пожалуйста, введите корректный email родителя");
        return false;
      }
      const phoneValidation = validatePhone(applicationData.parent_phone);
      if (!phoneValidation.isValid) {
        toast.error(phoneValidation.message!);
        return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (currentStep === 1 && !validateStep1()) return;
    if (currentStep === 2 && !validateStep2()) return;
    if (currentStep === 3 && !validateStep3()) return;
    
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    if (!validateStep3()) return;

    setIsLoading(true);

    try {
      const response = await djangoAPI.createApplication(applicationData);

      if (response.success && response.data) {
        toast.success("Заявка успешно подана!");
        const trackingToken = response.data.tracking_token;
        if (trackingToken) {
          navigate(`/application-status/${trackingToken}`);
        } else {
          toast.error("Ошибка: не получен tracking token");
        }
      } else {
        toast.error(response.error || "Ошибка при подаче заявки");
      }
    } catch (error: any) {
      console.error('Application error:', error);
      const errorMessage = error?.message || error?.error || "Произошла ошибка при подаче заявки";
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const renderStep1 = () => (
    <div className="space-y-4">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold mb-2">Личная информация</h2>
        <p className="text-muted-foreground">Укажите ваши основные данные</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="first_name">Имя *</Label>
          <Input
            id="first_name"
            value={applicationData.first_name}
            onChange={(e) => handleInputChange('first_name', e.target.value)}
            placeholder="Иван"
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="last_name">Фамилия *</Label>
          <Input
            id="last_name"
            value={applicationData.last_name}
            onChange={(e) => handleInputChange('last_name', e.target.value)}
            placeholder="Иванов"
            required
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="email">Email *</Label>
        <Input
          id="email"
          type="email"
          value={applicationData.email}
          onChange={(e) => handleInputChange('email', e.target.value)}
          placeholder="ivan@example.com"
          required
        />
        <ValidationMessage type="email" value={applicationData.email} />
      </div>

      <div className="space-y-2">
        <Label htmlFor="phone">Телефон *</Label>
        <Input
          id="phone"
          type="tel"
          value={applicationData.phone}
          onChange={(e) => handleInputChange('phone', e.target.value)}
          placeholder="+79991234567"
          required
        />
        <ValidationMessage type="phone" value={applicationData.phone} />
      </div>

      <div className="space-y-2">
        <Label htmlFor="telegram_id">Telegram ID (необязательно)</Label>
        <Input
          id="telegram_id"
          value={applicationData.telegram_id}
          onChange={(e) => handleInputChange('telegram_id', e.target.value)}
          placeholder="@username или 123456789"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="applicant_type">Тип заявки *</Label>
        <Select value={applicationData.applicant_type} onValueChange={(value) => handleInputChange('applicant_type', value)}>
          <SelectTrigger>
            <SelectValue placeholder="Выберите тип заявки" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="student">Студент</SelectItem>
            <SelectItem value="teacher">Преподаватель</SelectItem>
            <SelectItem value="parent">Родитель</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-4">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold mb-2">Дополнительная информация</h2>
        <p className="text-muted-foreground">
          {applicationData.applicant_type === "student" 
            ? "Укажите информацию о вашем обучении"
            : applicationData.applicant_type === "teacher"
            ? "Укажите информацию о вашем преподавании"
            : "Укажите дополнительную информацию"
          }
        </p>
      </div>

      {applicationData.applicant_type === "student" && (
        <>
          <div className="space-y-2">
            <Label htmlFor="grade">Класс *</Label>
            <Input
              id="grade"
              value={applicationData.grade}
              onChange={(e) => handleInputChange('grade', e.target.value)}
              placeholder="10"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="motivation">Цель обучения *</Label>
            <Textarea
              id="motivation"
              value={applicationData.motivation}
              onChange={(e) => handleInputChange('motivation', e.target.value)}
              placeholder="Хочу изучать программирование..."
              required
            />
          </div>
        </>
      )}

      {applicationData.applicant_type === "teacher" && (
        <>
          <div className="space-y-2">
            <Label htmlFor="subject">Предмет *</Label>
            <Input
              id="subject"
              value={applicationData.subject}
              onChange={(e) => handleInputChange('subject', e.target.value)}
              placeholder="Математика"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="experience">Опыт работы *</Label>
            <Textarea
              id="experience"
              value={applicationData.experience}
              onChange={(e) => handleInputChange('experience', e.target.value)}
              placeholder="5 лет преподавания математики в школе..."
              required
            />
          </div>
        </>
      )}

      <div className="space-y-2">
        <Label htmlFor="motivation">Дополнительная информация</Label>
        <Textarea
          id="motivation"
          value={applicationData.motivation}
          onChange={(e) => handleInputChange('motivation', e.target.value)}
          placeholder="Любая дополнительная информация..."
        />
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="space-y-4">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold mb-2">Информация о родителях</h2>
        <p className="text-muted-foreground">
          {applicationData.applicant_type === "student" 
            ? "Укажите данные родителей для связи"
            : "Эта информация не требуется для вашего типа заявки"
          }
        </p>
      </div>

      {applicationData.applicant_type === "student" && (
        <>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="parent_first_name">Имя родителя *</Label>
              <Input
                id="parent_first_name"
                value={applicationData.parent_first_name}
                onChange={(e) => handleInputChange('parent_first_name', e.target.value)}
                placeholder="Анна"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="parent_last_name">Фамилия родителя *</Label>
              <Input
                id="parent_last_name"
                value={applicationData.parent_last_name}
                onChange={(e) => handleInputChange('parent_last_name', e.target.value)}
                placeholder="Иванова"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="parent_email">Email родителя *</Label>
            <Input
              id="parent_email"
              type="email"
              value={applicationData.parent_email}
              onChange={(e) => handleInputChange('parent_email', e.target.value)}
              placeholder="anna@example.com"
              required
            />
            <ValidationMessage type="email" value={applicationData.parent_email} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="parent_phone">Телефон родителя *</Label>
            <Input
              id="parent_phone"
              type="tel"
              value={applicationData.parent_phone}
              onChange={(e) => handleInputChange('parent_phone', e.target.value)}
              placeholder="+79991234568"
              required
            />
            <ValidationMessage type="phone" value={applicationData.parent_phone} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="parent_telegram_id">Telegram ID родителя (необязательно)</Label>
            <Input
              id="parent_telegram_id"
              value={applicationData.parent_telegram_id}
              onChange={(e) => handleInputChange('parent_telegram_id', e.target.value)}
              placeholder="@parent_username или 123456789"
            />
          </div>
        </>
      )}
    </div>
  );

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-background via-muted/20 to-background">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-10 h-10 gradient-primary rounded-lg flex items-center justify-center">
                <BookOpen className="w-6 h-6 text-primary-foreground" />
              </div>
              <span className="text-2xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                THE BOT
              </span>
            </Link>
            <Link to="/" className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span>На главную</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Progress Bar */}
      <div className="border-b bg-card/30">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Шаг {currentStep} из {totalSteps}</span>
            </div>
            <div className="flex-1 max-w-md mx-4">
              <div className="w-full bg-muted rounded-full h-2">
                <div 
                  className="bg-primary h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(currentStep / totalSteps) * 100}%` }}
                />
              </div>
            </div>
            <div className="text-sm text-muted-foreground">
              {Math.round((currentStep / totalSteps) * 100)}%
            </div>
          </div>
        </div>
      </div>

      {/* Form */}
      <div className="flex-1 flex items-center justify-center p-4">
        <Card className="w-full max-w-2xl p-8 shadow-lg">
          {currentStep === 1 && renderStep1()}
          {currentStep === 2 && renderStep2()}
          {currentStep === 3 && renderStep3()}

          <div className="flex justify-between mt-8">
            <Button
              type="button"
              variant="outline"
              onClick={handlePrevious}
              disabled={currentStep === 1}
            >
              Назад
            </Button>
            
            {currentStep < totalSteps ? (
              <Button onClick={handleNext}>
                Далее
              </Button>
            ) : (
              <Button 
                onClick={handleSubmit}
                disabled={isLoading}
                className="gradient-primary shadow-glow"
              >
                {isLoading ? "Отправка..." : "Подать заявку"}
              </Button>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default ApplicationForm;
