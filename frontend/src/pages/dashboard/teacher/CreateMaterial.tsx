import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { ArrowLeft, Upload, FileText, Users, Tag, AlertCircle } from "lucide-react";

interface Subject {
  id: number;
  name: string;
  description: string;
  color: string;
}

interface Student {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

const CreateMaterial = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  // Форма материала
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    content: '',
    subject: '',
    type: 'lesson',
    status: 'draft',
    is_public: false,
    tags: '',
    difficulty_level: 1,
    assigned_to: [] as number[],
    video_url: ''
  });
  
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  // Загрузка данных
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Загружаем предметы
        const subjectsResponse = await apiClient.request<any>('/materials/subjects/');
        if (subjectsResponse.data) {
          const items = Array.isArray(subjectsResponse.data)
            ? subjectsResponse.data
            : (subjectsResponse.data.results ?? []);
          setSubjects(items as Subject[]);
        }
        
        // Студентов загружаем после выбора предмета
      } catch (error) {
        console.error('Error fetching data:', error);
        toast({
          title: "Ошибка загрузки данных",
          description: "Не удалось загрузить предметы и студентов",
          variant: "destructive"
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [toast]);

  // Загрузка студентов после выбора предмета
  useEffect(() => {
    const loadStudents = async () => {
      if (!formData.subject) {
        setStudents([]);
        return;
      }
      try {
        const resp = await apiClient.request<{students:{id:number; name:string; email:string}[]}>(`/materials/teacher/subjects/${formData.subject}/students/`);
        if (resp.data?.students) {
          const mapped: Student[] = resp.data.students.map(s => ({ id: s.id, first_name: s.name, last_name: '', email: s.email }));
          setStudents(mapped);
          // Сбрасываем выбор, если он не соответствует текущему списку
          setFormData(prev => ({
            ...prev,
            assigned_to: prev.assigned_to.filter(id => resp.data!.students.some(s => s.id === id))
          }));
        } else {
          setStudents([]);
        }
      } catch (e) {
        setStudents([]);
      }
    };
    loadStudents();
  }, [formData.subject]);

  // Валидация файла
  const validateFile = (file: File) => {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'jpg', 'jpeg', 'png'];
    
    if (file.size > maxSize) {
      setFileError(`Размер файла не должен превышать ${maxSize / (1024 * 1024)}MB`);
      return false;
    }
    
    const fileExtension = file.name.split('.').pop()?.toLowerCase();
    if (!fileExtension || !allowedTypes.includes(fileExtension)) {
      setFileError(`Неподдерживаемый тип файла. Разрешенные форматы: ${allowedTypes.join(', ')}`);
      return false;
    }
    
    setFileError(null);
    return true;
  };

  // Обработка загрузки файла
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      if (validateFile(selectedFile)) {
        setFile(selectedFile);
      }
    }
  };

  // Обработка изменений в форме
  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Обработка выбора студентов
  const handleStudentToggle = (studentId: number) => {
    setFormData(prev => ({
      ...prev,
      assigned_to: prev.assigned_to.includes(studentId)
        ? prev.assigned_to.filter(id => id !== studentId)
        : [...prev.assigned_to, studentId]
    }));
  };

  // Валидация формы
  const validateForm = () => {
    if (!formData.title.trim()) {
      toast({
        title: "Ошибка валидации",
        description: "Заголовок обязателен",
        variant: "destructive"
      });
      return false;
    }
    
    if (!formData.content.trim()) {
      toast({
        title: "Ошибка валидации",
        description: "Содержание обязательно",
        variant: "destructive"
      });
      return false;
    }
    
    if (!formData.subject) {
      toast({
        title: "Ошибка валидации",
        description: "Выберите предмет",
        variant: "destructive"
      });
      return false;
    }
    
    return true;
  };

  // Отправка формы
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    try {
      setSubmitting(true);
      
      // Создаем FormData для отправки файла
      const formDataToSend = new FormData();
      formDataToSend.append('title', formData.title);
      formDataToSend.append('description', formData.description);
      formDataToSend.append('content', formData.content);
      formDataToSend.append('subject', formData.subject);
      formDataToSend.append('type', formData.type);
      formDataToSend.append('status', formData.status);
      formDataToSend.append('is_public', formData.is_public.toString());
      formDataToSend.append('tags', formData.tags);
      formDataToSend.append('difficulty_level', formData.difficulty_level.toString());
      formDataToSend.append('video_url', formData.video_url);
      
      // Добавляем назначенных студентов
      formData.assigned_to.forEach(studentId => {
        formDataToSend.append('assigned_to', studentId.toString());
      });
      
      // Добавляем файл если есть
      if (file) {
        formDataToSend.append('file', file);
      }
      
      const response = await apiClient.request('/materials/materials/', {
        method: 'POST',
        body: formDataToSend,
        headers: {
          // Не устанавливаем Content-Type, браузер сам установит с boundary
        }
      });
      
      if (response.data) {
        toast({
          title: "Материал создан",
          description: "Материал успешно создан и сохранен",
        });
        navigate('/dashboard/teacher/materials');
      } else {
        throw new Error(response.error || 'Ошибка создания материала');
      }
    } catch (error) {
      console.error('Error creating material:', error);
      toast({
        title: "Ошибка создания материала",
        description: error instanceof Error ? error.message : "Произошла неизвестная ошибка",
        variant: "destructive"
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <SidebarProvider>
        <div className="flex min-h-screen w-full">
          <TeacherSidebar />
          <SidebarInset>
            <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
              <SidebarTrigger />
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                <h1 className="text-lg font-semibold">Создание материала</h1>
              </div>
            </header>
            <main className="flex flex-1 flex-col gap-4 p-4">
              <Card className="p-6">
                <div className="text-center">Загрузка...</div>
              </Card>
            </main>
          </SidebarInset>
        </div>
      </SidebarProvider>
    );
  }

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TeacherSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              <h1 className="text-lg font-semibold">Создание материала</h1>
            </div>
          </header>
          <main className="flex flex-1 flex-col gap-4 p-4">
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate('/dashboard/teacher/materials')}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Назад к материалам
              </Button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                {/* Основная информация */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">Основная информация</h3>
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="title">Заголовок *</Label>
                      <Input
                        id="title"
                        value={formData.title}
                        onChange={(e) => handleInputChange('title', e.target.value)}
                        placeholder="Введите заголовок материала"
                        required
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="description">Описание</Label>
                      <Textarea
                        id="description"
                        value={formData.description}
                        onChange={(e) => handleInputChange('description', e.target.value)}
                        placeholder="Краткое описание материала"
                        rows={3}
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="subject">Предмет *</Label>
                      <Select
                        value={formData.subject}
                        onValueChange={(value) => handleInputChange('subject', value)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Выберите предмет" />
                        </SelectTrigger>
                        <SelectContent>
                          {(subjects || []).map((subject) => (
                            <SelectItem key={subject.id} value={subject.id.toString()}>
                              {subject.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <Label htmlFor="type">Тип материала</Label>
                      <Select
                        value={formData.type}
                        onValueChange={(value) => handleInputChange('type', value)}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="lesson">Урок</SelectItem>
                          <SelectItem value="presentation">Презентация</SelectItem>
                          <SelectItem value="video">Видео</SelectItem>
                          <SelectItem value="document">Документ</SelectItem>
                          <SelectItem value="test">Тест</SelectItem>
                          <SelectItem value="homework">Домашнее задание</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </Card>

                {/* Дополнительные настройки */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">Дополнительные настройки</h3>
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="difficulty_level">Уровень сложности</Label>
                      <Select
                        value={formData.difficulty_level.toString()}
                        onValueChange={(value) => handleInputChange('difficulty_level', parseInt(value))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {[1, 2, 3, 4, 5].map((level) => (
                            <SelectItem key={level} value={level.toString()}>
                              Уровень {level}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <Label htmlFor="status">Статус</Label>
                      <Select
                        value={formData.status}
                        onValueChange={(value) => handleInputChange('status', value)}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="draft">Черновик</SelectItem>
                          <SelectItem value="active">Активно</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="is_public"
                        checked={formData.is_public}
                        onCheckedChange={(checked) => handleInputChange('is_public', checked)}
                      />
                      <Label htmlFor="is_public">Публичный материал</Label>
                    </div>
                    
                    <div>
                      <Label htmlFor="tags">Теги</Label>
                      <Input
                        id="tags"
                        value={formData.tags}
                        onChange={(e) => handleInputChange('tags', e.target.value)}
                        placeholder="Введите теги через запятую"
                      />
                    </div>
                  </div>
                </Card>
              </div>

              {/* Содержание */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Содержание *</h3>
                <Textarea
                  value={formData.content}
                  onChange={(e) => handleInputChange('content', e.target.value)}
                  placeholder="Введите содержание материала"
                  rows={8}
                  required
                />
              </Card>

              {/* Файлы и медиа */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Файлы и медиа</h3>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="file">Файл материала</Label>
                    <div className="mt-2">
                      <Input
                        id="file"
                        type="file"
                        onChange={handleFileChange}
                        accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.jpg,.jpeg,.png"
                      />
                      {fileError && (
                        <div className="flex items-center gap-2 mt-2 text-destructive">
                          <AlertCircle className="h-4 w-4" />
                          <span className="text-sm">{fileError}</span>
                        </div>
                      )}
                      {file && (
                        <div className="mt-2">
                          <Badge variant="outline">
                            <FileText className="h-3 w-3 mr-1" />
                            {file.name}
                          </Badge>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div>
                    <Label htmlFor="video_url">Ссылка на видео</Label>
                    <Input
                      id="video_url"
                      type="url"
                      value={formData.video_url}
                      onChange={(e) => handleInputChange('video_url', e.target.value)}
                      placeholder="https://youtube.com/watch?v=..."
                    />
                  </div>
                </div>
              </Card>

              {/* Назначение студентам */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Назначение студентам</h3>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {students.map((student) => (
                    <div key={student.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={`student-${student.id}`}
                        checked={formData.assigned_to.includes(student.id)}
                        onCheckedChange={() => handleStudentToggle(student.id)}
                      />
                      <Label htmlFor={`student-${student.id}`} className="flex-1">
                        {student.first_name} {student.last_name} ({student.email})
                      </Label>
                    </div>
                  ))}
                </div>
                {formData.assigned_to.length > 0 && (
                  <div className="mt-4">
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4" />
                      <span className="text-sm text-muted-foreground">
                        Назначено {formData.assigned_to.length} студентам
                      </span>
                    </div>
                  </div>
                )}
              </Card>

              {/* Кнопки действий */}
              <div className="flex justify-end gap-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate('/dashboard/teacher/materials')}
                >
                  Отмена
                </Button>
                <Button
                  type="submit"
                  disabled={submitting}
                  className="gradient-primary shadow-glow"
                >
                  {submitting ? 'Создание...' : 'Создать материал'}
                </Button>
              </div>
            </form>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default CreateMaterial;
