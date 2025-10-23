import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { djangoAPI } from "@/integrations/django/client";

export const ApplicationForm = () => {
  const [formData, setFormData] = useState({
    studentName: "",
    parentName: "",
    phone: "",
    email: "",
    grade: "",
    goal: "",
    message: ""
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    if (!formData.studentName || !formData.parentName || !formData.phone || !formData.email || !formData.grade) {
      toast.error("Пожалуйста, заполните все обязательные поля");
      return;
    }

    try {
      // Отправляем заявку в Django API
      const applicationData = {
        student_name: formData.studentName,
        parent_name: formData.parentName,
        phone: formData.phone,
        email: formData.email,
        grade: parseInt(formData.grade),
        goal: formData.goal || undefined,
        message: formData.message || undefined,
      };

      const response = await djangoAPI.createApplication(applicationData);
      
      console.log("Application submitted:", response);
      toast.success("Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.");
      
      // Reset form
      setFormData({
        studentName: "",
        parentName: "",
        phone: "",
        email: "",
        grade: "",
        goal: "",
        message: ""
      });
    } catch (error) {
      console.error("Error submitting application:", error);
      toast.error("Произошла ошибка при отправке заявки. Попробуйте еще раз.");
    }
  };

  return (
    <Card className="p-6 md:p-8">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="studentName">Имя ученика *</Label>
          <Input
            id="studentName"
            value={formData.studentName}
            onChange={(e) => setFormData({ ...formData, studentName: e.target.value })}
            placeholder="Иван Иванов"
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="parentName">Имя родителя *</Label>
          <Input
            id="parentName"
            value={formData.parentName}
            onChange={(e) => setFormData({ ...formData, parentName: e.target.value })}
            placeholder="Иван Иванович"
            required
          />
        </div>

        <div className="grid md:grid-cols-2 gap-4">
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

        <div className="space-y-2">
          <Label htmlFor="goal">Образовательная цель</Label>
          <Input
            id="goal"
            value={formData.goal}
            onChange={(e) => setFormData({ ...formData, goal: e.target.value })}
            placeholder="Например: Подготовка к ОГЭ/ЕГЭ, углубленное изучение предмета"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="message">Дополнительная информация</Label>
          <Textarea
            id="message"
            value={formData.message}
            onChange={(e) => setFormData({ ...formData, message: e.target.value })}
            placeholder="Расскажите о предпочтениях и особенностях обучения"
            rows={4}
          />
        </div>

        <Button type="submit" className="w-full gradient-primary shadow-glow hover:opacity-90 transition-opacity">
          Отправить заявку
        </Button>
      </form>
    </Card>
  );
};
