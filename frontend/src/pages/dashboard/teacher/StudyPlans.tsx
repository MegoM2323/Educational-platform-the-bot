import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Calendar, Send, Plus, FileText, Clock, User, BookOpen, Edit, Upload, X, Download, Trash2, AlertCircle } from "lucide-react";
import { useState, useEffect } from "react";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";
import { cacheService } from "@/services/cacheService";
import { useToast } from "@/hooks/use-toast";
import { useErrorNotification, useSuccessNotification } from "@/components/NotificationSystem";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import { handleProtectedFileClick } from "@/utils/fileDownload";
import { getFileIcon, getFileIconColor, formatFileSize, validateFileSize } from "@/utils/fileUtils";
import { Progress } from "@/components/ui/progress";

interface StudyPlanFile {
  id: number;
  name: string;
  file_url: string;
  file_size: number;
  uploaded_by_name: string;
  created_at: string;
}

interface StudyPlan {
  id: number;
  title: string;
  content: string;
  week_start_date: string;
  week_end_date: string;
  status: 'draft' | 'sent' | 'archived';
  student_name: string;
  student: number;
  subject_name: string;
  subject_color: string;
  subject: number;
  sent_at?: string;
  created_at: string;
  files?: StudyPlanFile[];
}

interface Subject {
  id: number;
  name: string;
  color: string;
  is_assigned?: boolean;
}

interface Student {
  id: number;
  name: string;
  email: string;
  subjects?: Array<{
    id: number;
    name: string;
    color: string;
  }>;
}

export default function StudyPlans() {
  const { toast } = useToast();
  const showError = useErrorNotification();
  const showSuccess = useSuccessNotification();

  const [plans, setPlans] = useState<StudyPlan[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [availableStudents, setAvailableStudents] = useState<Student[]>([]); // Студенты для выбранного предмета
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSubject, setSelectedSubject] = useState<string>("all");
  const [selectedStudent, setSelectedStudent] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<StudyPlan | null>(null);
  const [sendingPlanId, setSendingPlanId] = useState<number | null>(null);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [uploadingFile, setUploadingFile] = useState<number | null>(null);
  const [deletingFile, setDeletingFile] = useState<number | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [createPlanFiles, setCreatePlanFiles] = useState<File[]>([]);
  const [uploadingCreateFiles, setUploadingCreateFiles] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});

  // Форма создания плана
  const [formData, setFormData] = useState({
    student: '',
    subject: '',
    title: '',
    content: '',
    week_start_date: '',
    status: 'draft' as 'draft' | 'sent'
  });

  // Загрузка планов
  const fetchPlans = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (selectedSubject !== "all") params.append('subject_id', selectedSubject);
      if (selectedStudent !== "all") params.append('student_id', selectedStudent);
      if (selectedStatus !== "all") params.append('status', selectedStatus);

      const response = await apiClient.request<{ study_plans: StudyPlan[] }>(
        `/materials/teacher/study-plans/?${params.toString()}`
      );

      if (response.data) {
        const plansData = response.data.study_plans || [];
        console.log('Loaded plans:', plansData);
        console.log('Plans with files:', plansData.filter(p => p.files && p.files.length > 0));
        setPlans(plansData);
      } else {
        const errorMessage = response.error || 'Ошибка загрузки планов';
        setError(errorMessage);
        showError(errorMessage);
      }
    } catch (err: any) {
      const errorMessage = 'Произошла ошибка при загрузке планов';
      setError(errorMessage);
      showError(errorMessage);
      console.error('Study plans fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Загрузка предметов преподавателя
  const fetchSubjects = async () => {
    try {
      const response = await apiClient.request<{ subjects: Subject[] } | Subject[]>('/materials/teacher/subjects/');
      if (response.data) {
        // Проверяем формат ответа - может быть массив или объект с полем subjects
        const subjectsList = Array.isArray(response.data)
          ? response.data
          : response.data.subjects ?? [];

        const assignedSubjects = subjectsList.filter(subject => subject.is_assigned);
        if (assignedSubjects.length === 0) {
          if (subjectsList.length > 0) {
            showError('У вас нет назначенных предметов. Сначала назначьте предмет себе.');
          }
          setSubjects(subjectsList);
        } else {
          setSubjects(assignedSubjects);
        }
      }
    } catch (err) {
      console.error('Subjects fetch error:', err);
      showError('Ошибка загрузки предметов');
    }
  };

  // Загрузка студентов по предмету
  const fetchStudentsForSubject = async (subjectId: number) => {
    try {
      console.log('[StudyPlans] Fetching students for subject:', subjectId);
      const response = await apiClient.request<{ students: Array<{id: number; name: string; email: string}> }>(
        `/materials/teacher/subjects/${subjectId}/students/`
      );
      console.log('[StudyPlans] Students response:', response);
      if (response.data?.students) {
        const students = response.data.students.map(s => ({
          id: s.id,
          name: s.name,
          email: s.email
        }));
        console.log('[StudyPlans] Available students:', students);
        return students;
      }
      console.warn('[StudyPlans] No students found in response');
      return [];
    } catch (err) {
      console.error('[StudyPlans] Students fetch error:', err);
      return [];
    }
  };

  useEffect(() => {
    fetchPlans();
  }, [selectedSubject, selectedStudent, selectedStatus]);

  useEffect(() => {
    fetchSubjects();
    // Загружаем всех студентов для фильтра
    const loadAllStudents = async () => {
      try {
        const response = await apiClient.request<{ students: Student[] }>('/materials/dashboard/teacher/students/');
        if (response.data?.students) {
          setStudents(response.data.students);
        }
      } catch (err) {
        console.error('Students fetch error:', err);
      }
    };
    loadAllStudents();
  }, []);

  // Загрузка студентов при выборе предмета в форме создания
  useEffect(() => {
    const loadStudentsForSubject = async () => {
      if (formData.subject && formData.subject !== '') {
        console.log('[StudyPlans] Loading students for selected subject:', formData.subject);
        setLoadingStudents(true);
        const studentsList = await fetchStudentsForSubject(parseInt(formData.subject));
        console.log('[StudyPlans] Students loaded, count:', studentsList.length);
        setAvailableStudents(studentsList);
        setLoadingStudents(false);
        // Сбрасываем выбранного студента при смене предмета
        setFormData(prev => ({...prev, student: ''}));
      } else {
        console.log('[StudyPlans] No subject selected, clearing students');
        setAvailableStudents([]);
      }
    };
    loadStudentsForSubject();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData.subject]);

  // Создание плана
  const handleCreatePlan = async () => {
    // Детальная валидация с отладочной информацией
    const missingFields: string[] = [];
    if (!formData.student) missingFields.push('Студент');
    if (!formData.subject) missingFields.push('Предмет');
    if (!formData.title) missingFields.push('Название плана');
    if (!formData.content) missingFields.push('Содержание плана');
    if (!formData.week_start_date) missingFields.push('Дата начала недели');

    if (missingFields.length > 0) {
      console.log('[StudyPlans] Missing fields:', missingFields);
      console.log('[StudyPlans] Form data:', formData);
      showError(`Заполните все обязательные поля: ${missingFields.join(', ')}`);
      return;
    }

    // Валидация размера файлов (10MB максимум)
    const maxFileSizeMB = 10;
    for (const file of createPlanFiles) {
      const validation = validateFileSize(file, maxFileSizeMB);
      if (!validation.isValid) {
        showError(validation.error || 'Файл слишком большой');
        return;
      }
    }

    try {
      setUploadingCreateFiles(true);
      setUploadProgress({});
      
      // Создаем план
      const response = await apiClient.request<StudyPlan>('/materials/teacher/study-plans/', {
        method: 'POST',
        body: JSON.stringify({
          student: parseInt(formData.student),
          subject: parseInt(formData.subject),
          title: formData.title,
          content: formData.content,
          week_start_date: formData.week_start_date,
          status: formData.status
        })
      });

      if (response.data) {
        const createdPlanId = response.data.id;
        
        // Загружаем файлы, если они есть
        if (createPlanFiles.length > 0) {
          try {
            for (let i = 0; i < createPlanFiles.length; i++) {
              const file = createPlanFiles[i];
              const fileKey = `${file.name}-${i}`;

              setUploadProgress(prev => ({ ...prev, [fileKey]: 0 }));

              const formData = new FormData();
              formData.append('file', file);

              // Simulate progress (real progress requires XMLHttpRequest)
              const progressInterval = setInterval(() => {
                setUploadProgress(prev => {
                  const current = prev[fileKey] || 0;
                  if (current < 90) {
                    return { ...prev, [fileKey]: current + 10 };
                  }
                  return prev;
                });
              }, 100);

              try {
                await apiClient.request<StudyPlanFile>(`/materials/teacher/study-plans/${createdPlanId}/files/`, {
                  method: 'POST',
                  body: formData,
                });
                clearInterval(progressInterval);
                setUploadProgress(prev => ({ ...prev, [fileKey]: 100 }));
              } catch (err) {
                clearInterval(progressInterval);
                throw err;
              }
            }
          } catch (fileErr: any) {
            console.error('Error uploading files:', fileErr);
            showError('План создан, но не все файлы удалось загрузить');
          }
        }
        
        showSuccess('План занятий создан');
        setCreateDialogOpen(false);
        setFormData({
          student: '',
          subject: '',
          title: '',
          content: '',
          week_start_date: '',
          status: 'draft'
        });
        setCreatePlanFiles([]);
        setAvailableStudents([]);
        // Инвалидируем кэш списка планов, чтобы сразу увидеть изменения
        cacheService.keys().forEach((key) => {
          if (key.startsWith('/materials/teacher/study-plans/')) {
            cacheService.delete(key);
          }
        });
        fetchPlans();
      } else {
        showError(response.error || 'Ошибка при создании плана');
      }
    } catch (err: any) {
      showError('Произошла ошибка при создании плана');
      console.error('Create plan error:', err);
    } finally {
      setUploadingCreateFiles(false);
    }
  };

  // Редактирование плана
  const handleEditPlan = async () => {
    if (!selectedPlan || !formData.title || !formData.content || !formData.week_start_date) {
      showError('Заполните все обязательные поля');
      return;
    }

    try {
      const response = await apiClient.request<StudyPlan>(`/materials/teacher/study-plans/${selectedPlan.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({
          title: formData.title,
          content: formData.content,
          week_start_date: formData.week_start_date,
          status: formData.status
        })
      });

      if (response.data) {
        showSuccess('План занятий обновлен');
        setEditDialogOpen(false);
        cacheService.keys().forEach((key) => {
          if (key.startsWith('/materials/teacher/study-plans/')) {
            cacheService.delete(key);
          }
        });
        fetchPlans();
      } else {
        showError(response.error || 'Ошибка при обновлении плана');
      }
    } catch (err: any) {
      showError('Произошла ошибка при обновлении плана');
      console.error('Edit plan error:', err);
    }
  };

  // Открытие диалога редактирования
  const handleOpenEditDialog = async (plan: StudyPlan) => {
    // Проверяем, можно ли редактировать план
    if (plan.status === 'sent' || plan.status === 'archived') {
      showError('Нельзя редактировать отправленные или архивные планы занятий');
      return;
    }

    try {
      // Загружаем полные детали плана с файлами
      const response = await apiClient.request<StudyPlan>(`/materials/teacher/study-plans/${plan.id}/`);
      if (response.data) {
        setSelectedPlan(response.data);
        setFormData({
          student: response.data.student.toString(),
          subject: response.data.subject.toString(),
          title: response.data.title,
          content: response.data.content,
          week_start_date: response.data.week_start_date,
          status: response.data.status
        });
        setEditDialogOpen(true);
      } else {
        showError('Ошибка при загрузке деталей плана');
      }
    } catch (err: any) {
      showError('Произошла ошибка при загрузке деталей плана');
      console.error('Load plan details error:', err);
    }
  };

  // Загрузка файла
  const handleUploadFile = async (planId: number, file: File) => {
    // Валидация размера файла (10MB максимум)
    const maxFileSizeMB = 10;
    const validation = validateFileSize(file, maxFileSizeMB);
    if (!validation.isValid) {
      showError(validation.error || 'Файл слишком большой');
      return;
    }

    try {
      setUploadingFile(planId);
      const formData = new FormData();
      formData.append('file', file);

      const response = await apiClient.request<StudyPlanFile>(`/materials/teacher/study-plans/${planId}/files/`, {
        method: 'POST',
        body: formData,
        // Не устанавливаем Content-Type - браузер установит его автоматически с boundary
      });

      if (response.data) {
        showSuccess('Файл загружен');
        cacheService.keys().forEach((key) => {
          if (key.startsWith('/materials/teacher/study-plans/')) {
            cacheService.delete(key);
          }
        });
        // Обновляем выбранный план, чтобы файлы сразу отобразились
        if (selectedPlan && selectedPlan.id === planId) {
          const updatedPlanResponse = await apiClient.request<StudyPlan>(`/materials/teacher/study-plans/${planId}/`);
          if (updatedPlanResponse.data) {
            setSelectedPlan(updatedPlanResponse.data);
          }
        }
        fetchPlans();
      } else {
        showError(response.error || 'Ошибка при загрузке файла');
      }
    } catch (err: any) {
      showError('Произошла ошибка при загрузке файла');
      console.error('Upload file error:', err);
    } finally {
      setUploadingFile(null);
    }
  };

  // Удаление файла
  const handleDeleteFile = async (planId: number, fileId: number) => {
    if (!confirm('Вы уверены, что хотите удалить этот файл?')) {
      return;
    }

    try {
      setDeletingFile(fileId);
      const response = await apiClient.request(`/materials/teacher/study-plans/${planId}/files/${fileId}/`, {
        method: 'DELETE'
      });

      if (response.data || response.status === 204) {
        showSuccess('Файл удален');
        cacheService.keys().forEach((key) => {
          if (key.startsWith('/materials/teacher/study-plans/')) {
            cacheService.delete(key);
          }
        });
        fetchPlans();
      } else {
        showError(response.error || 'Ошибка при удалении файла');
      }
    } catch (err: any) {
      showError('Произошла ошибка при удалении файла');
      console.error('Delete file error:', err);
    } finally {
      setDeletingFile(null);
    }
  };

  // Отправка плана
  const handleSendPlan = async (planId: number) => {
    try {
      setSendingPlanId(planId);
      const response = await apiClient.request<StudyPlan>(`/materials/teacher/study-plans/${planId}/send/`, {
        method: 'POST'
      });

      if (response.data) {
        showSuccess('План занятий отправлен студенту');
        cacheService.keys().forEach((key) => {
          if (key.startsWith('/materials/teacher/study-plans/')) {
            cacheService.delete(key);
          }
          if (key.startsWith('/student/study-plans/')) {
            cacheService.delete(key);
          }
        });
        fetchPlans();
      } else {
        showError(response.error || 'Ошибка при отправке плана');
      }
    } catch (err: any) {
      showError('Произошла ошибка при отправке плана');
      console.error('Send plan error:', err);
    } finally {
      setSendingPlanId(null);
    }
  };

  // Получение студентов для выбранного предмета (для фильтра в списке планов)
  const getStudentsForSubject = async (subjectId: string) => {
    if (subjectId === "all" || !subjectId) {
      // Загружаем всех студентов преподавателя
      try {
        const response = await apiClient.request<{ students: Student[] }>('/materials/dashboard/teacher/students/');
        if (response.data?.students) {
          return response.data.students;
        }
      } catch (err) {
        console.error('Students fetch error:', err);
      }
      return [];
    }
    // Загружаем студентов по предмету
    return await fetchStudentsForSubject(parseInt(subjectId));
  };

  const filteredPlans = plans;

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TeacherSidebar />
        <SidebarInset className="flex-1">
          <div className="flex items-center gap-4 border-b p-4">
            <SidebarTrigger />
            <h1 className="text-2xl font-bold">Планы занятий</h1>
          </div>
          <main className="p-6 space-y-6">
            {/* Фильтры и действия */}
            <Card className="p-4">
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex-1 min-w-[200px]">
                  <Label>Предмет</Label>
                  <Select value={selectedSubject} onValueChange={setSelectedSubject}>
                    <SelectTrigger>
                      <SelectValue placeholder="Все предметы" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Все предметы</SelectItem>
                      {subjects.map(subject => (
                        <SelectItem key={subject.id} value={subject.id.toString()}>
                          {subject.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1 min-w-[200px]">
                  <Label>Студент</Label>
                  <Select value={selectedStudent} onValueChange={setSelectedStudent}>
                    <SelectTrigger>
                      <SelectValue placeholder="Все студенты" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Все студенты</SelectItem>
                      {students.map(student => (
                        <SelectItem key={student.id} value={student.id.toString()}>
                          {student.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1 min-w-[200px]">
                  <Label>Статус</Label>
                  <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                    <SelectTrigger>
                      <SelectValue placeholder="Все статусы" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Все статусы</SelectItem>
                      <SelectItem value="draft">Черновик</SelectItem>
                      <SelectItem value="sent">Отправлен</SelectItem>
                      <SelectItem value="archived">Архив</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Dialog open={createDialogOpen} onOpenChange={(open) => {
                  setCreateDialogOpen(open);
                  if (!open) {
                    // Сбрасываем форму при закрытии диалога
                    setFormData({
                      student: '',
                      subject: '',
                      title: '',
                      content: '',
                      week_start_date: '',
                      status: 'draft'
                    });
                    setCreatePlanFiles([]);
                    setAvailableStudents([]);
                  }
                }}>
                  <DialogTrigger asChild>
                    <Button>
                      <Plus className="w-4 h-4 mr-2" />
                      Создать план
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                      <DialogTitle>Создать план занятий</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                      <div>
                        <Label>Предмет *</Label>
                        <Select 
                          value={formData.subject} 
                          onValueChange={(value) => setFormData({...formData, subject: value})}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Выберите предмет" />
                          </SelectTrigger>
                          <SelectContent>
                            {subjects.map(subject => (
                              <SelectItem key={subject.id} value={subject.id.toString()}>
                                {subject.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>Студент *</Label>
                        <Select 
                          value={formData.student} 
                          onValueChange={(value) => setFormData({...formData, student: value})}
                          disabled={!formData.subject || loadingStudents}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder={formData.subject ? (loadingStudents ? "Загрузка..." : "Выберите студента") : "Сначала выберите предмет"} />
                          </SelectTrigger>
                          <SelectContent>
                            {availableStudents.length === 0 && formData.subject ? (
                              <div className="px-2 py-1 text-sm text-muted-foreground">
                                Нет студентов на этом предмете
                              </div>
                            ) : (
                              availableStudents.map(student => (
                                <SelectItem key={student.id} value={student.id.toString()}>
                                  {student.name}
                                </SelectItem>
                              ))
                            )}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>Название плана *</Label>
                        <Input
                          value={formData.title}
                          onChange={(e) => setFormData({...formData, title: e.target.value})}
                          placeholder="Например: Неделя 1: Алгебра"
                        />
                      </div>
                      <div>
                        <Label>Дата начала недели *</Label>
                        <Input
                          type="date"
                          value={formData.week_start_date}
                          onChange={(e) => setFormData({...formData, week_start_date: e.target.value})}
                          required
                        />
                      </div>
                      <div>
                        <Label>Содержание плана *</Label>
                        <Textarea
                          value={formData.content}
                          onChange={(e) => setFormData({...formData, content: e.target.value})}
                          placeholder="Опишите план занятий на неделю..."
                          rows={10}
                        />
                      </div>
                      <div>
                        <Label>Статус</Label>
                        <Select 
                          value={formData.status} 
                          onValueChange={(value) => setFormData({...formData, status: value as 'draft' | 'sent'})}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="draft">Черновик</SelectItem>
                            <SelectItem value="sent">Отправить сразу</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>Прикрепить файлы</Label>
                        <div className="mt-2 space-y-2">
                          <Input
                            type="file"
                            multiple
                            onChange={(e) => {
                              const files = Array.from(e.target.files || []);
                              // Validate file sizes before adding
                              const maxFileSizeMB = 10;
                              const invalidFiles: string[] = [];

                              files.forEach(file => {
                                const validation = validateFileSize(file, maxFileSizeMB);
                                if (!validation.isValid) {
                                  invalidFiles.push(validation.error || file.name);
                                }
                              });

                              if (invalidFiles.length > 0) {
                                showError(invalidFiles.join('\n'));
                                e.target.value = '';
                                return;
                              }

                              setCreatePlanFiles(prev => [...prev, ...files]);
                              e.target.value = '';
                            }}
                            accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.zip,.rar"
                          />
                          <p className="text-xs text-muted-foreground flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" />
                            Максимальный размер файла: 10 MB
                          </p>
                          {createPlanFiles.length > 0 && (
                            <div className="space-y-2 mt-2">
                              {createPlanFiles.map((file, index) => {
                                const FileIcon = getFileIcon(file.name);
                                const iconColor = getFileIconColor(file.name);
                                const fileKey = `${file.name}-${index}`;
                                const progress = uploadProgress[fileKey];

                                return (
                                  <div key={index} className="space-y-1">
                                    <div className="flex items-center justify-between p-2 bg-muted rounded-md">
                                      <div className="flex items-center gap-2 flex-1">
                                        <FileIcon className={`w-4 h-4 ${iconColor}`} />
                                        <span className="text-sm font-medium truncate">{file.name}</span>
                                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                                          {formatFileSize(file.size)}
                                        </span>
                                      </div>
                                      {!uploadingCreateFiles && (
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          onClick={() => {
                                            setCreatePlanFiles(prev => prev.filter((_, i) => i !== index));
                                          }}
                                        >
                                          <X className="w-4 h-4 text-destructive" />
                                        </Button>
                                      )}
                                    </div>
                                    {uploadingCreateFiles && progress !== undefined && (
                                      <div className="space-y-1">
                                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                                          <span>Загрузка...</span>
                                          <span>{progress}%</span>
                                        </div>
                                        <Progress value={progress} className="h-1" />
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                          Отмена
                        </Button>
                        <Button onClick={handleCreatePlan} disabled={uploadingCreateFiles}>
                          {uploadingCreateFiles ? 'Создание...' : 'Создать'}
                        </Button>
                      </div>
                    </div>
                  </DialogContent>
                </Dialog>
              </div>
            </Card>

            {/* Список планов */}
            {loading ? (
              <div className="text-center py-8">Загрузка...</div>
            ) : error ? (
              <div className="text-center py-8 text-destructive">{error}</div>
            ) : filteredPlans.length === 0 ? (
              <Card className="p-8 text-center">
                <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p className="text-muted-foreground">Нет планов занятий</p>
              </Card>
            ) : (
              <div className="grid gap-4">
                {filteredPlans.map(plan => (
                  <Card key={plan.id} className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <Badge 
                            style={{ backgroundColor: plan.subject_color }}
                            className="text-white"
                          >
                            {plan.subject_name}
                          </Badge>
                          <Badge variant={plan.status === 'sent' ? 'default' : 'outline'}>
                            {plan.status === 'sent' ? 'Отправлен' : plan.status === 'draft' ? 'Черновик' : 'Архив'}
                          </Badge>
                        </div>
                        <h3 className="text-xl font-bold mb-2">{plan.title}</h3>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                          <div className="flex items-center gap-1">
                            <User className="w-4 h-4" />
                            {plan.student_name}
                          </div>
                          <div className="flex items-center gap-1">
                            <Calendar className="w-4 h-4" />
                            {format(new Date(plan.week_start_date), "dd.MM.yyyy", { locale: ru })} - {format(new Date(plan.week_end_date), "dd.MM.yyyy", { locale: ru })}
                          </div>
                          {plan.sent_at && (
                            <div className="flex items-center gap-1">
                              <Clock className="w-4 h-4" />
                              Отправлен: {format(new Date(plan.sent_at), "dd.MM.yyyy HH:mm", { locale: ru })}
                            </div>
                          )}
                        </div>
                        <p className="text-muted-foreground line-clamp-2">{plan.content}</p>
                        {plan.files && plan.files.length > 0 && (
                          <div className="flex items-center gap-2 mt-2 text-sm text-muted-foreground">
                            <FileText className="w-4 h-4" />
                            <span>Прикреплено файлов: {plan.files.length}</span>
                          </div>
                        )}
                      </div>
                      <div className="flex gap-2 ml-4">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={async () => {
                            try {
                              // Загружаем полные детали плана с файлами
                              const response = await apiClient.request<StudyPlan>(`/materials/teacher/study-plans/${plan.id}/`);
                              if (response.data) {
                                setSelectedPlan(response.data);
                                setViewDialogOpen(true);
                              } else {
                                showError('Ошибка при загрузке деталей плана');
                              }
                            } catch (err: any) {
                              showError('Произошла ошибка при загрузке деталей плана');
                              console.error('Load plan details error:', err);
                            }
                          }}
                        >
                          <FileText className="w-4 h-4 mr-2" />
                          Просмотр
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleOpenEditDialog(plan)}
                          disabled={plan.status === 'sent' || plan.status === 'archived'}
                          title={plan.status === 'sent' || plan.status === 'archived' ? 'Нельзя редактировать отправленные или архивные планы' : ''}
                        >
                          <Edit className="w-4 h-4 mr-2" />
                          Редактировать
                        </Button>
                        {plan.status === 'draft' && (
                          <Button
                            variant="default"
                            size="sm"
                            onClick={() => handleSendPlan(plan.id)}
                            disabled={sendingPlanId === plan.id}
                          >
                            <Send className="w-4 h-4 mr-2" />
                            {sendingPlanId === plan.id ? 'Отправка...' : 'Отправить'}
                          </Button>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}

            {/* Диалог просмотра плана */}
            <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
              <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>
                    {selectedPlan?.title}
                  </DialogTitle>
                </DialogHeader>
                {selectedPlan && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <Badge 
                        style={{ backgroundColor: selectedPlan.subject_color }}
                        className="text-white"
                      >
                        {selectedPlan.subject_name}
                      </Badge>
                      <Badge variant={selectedPlan.status === 'sent' ? 'default' : 'outline'}>
                        {selectedPlan.status === 'sent' ? 'Отправлен' : selectedPlan.status === 'draft' ? 'Черновик' : 'Архив'}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <Label>Студент</Label>
                        <p className="font-medium">{selectedPlan.student_name}</p>
                      </div>
                      <div>
                        <Label>Период</Label>
                        <p className="font-medium">
                          {format(new Date(selectedPlan.week_start_date), "dd.MM.yyyy", { locale: ru })} - {format(new Date(selectedPlan.week_end_date), "dd.MM.yyyy", { locale: ru })}
                        </p>
                      </div>
                      {selectedPlan.sent_at && (
                        <div>
                          <Label>Отправлен</Label>
                          <p className="font-medium">
                            {format(new Date(selectedPlan.sent_at), "dd.MM.yyyy HH:mm", { locale: ru })}
                          </p>
                        </div>
                      )}
                    </div>
                    <div>
                      <Label>Содержание плана</Label>
                      <div className="mt-2 p-4 bg-muted rounded-md whitespace-pre-wrap">
                        {selectedPlan.content}
                      </div>
                    </div>
                    <div>
                      <Label>Прикрепленные файлы</Label>
                      <div className="mt-2 space-y-2">
                        {selectedPlan.files && selectedPlan.files.length > 0 ? (
                          selectedPlan.files.map((file) => {
                            const FileIcon = getFileIcon(file.name);
                            const iconColor = getFileIconColor(file.name);

                            return (
                              <div key={file.id} className="flex items-center justify-between p-3 bg-muted rounded-md hover:bg-muted/80 transition-colors">
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                  <FileIcon className={`w-4 h-4 flex-shrink-0 ${iconColor}`} />
                                  <a
                                    href={file.file_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sm font-medium hover:underline truncate"
                                    onClick={(e) => handleProtectedFileClick(e, file.file_url, file.name)}
                                  >
                                    {file.name}
                                  </a>
                                  <span className="text-xs text-muted-foreground whitespace-nowrap flex-shrink-0">
                                    {formatFileSize(file.file_size)}
                                  </span>
                                </div>
                              </div>
                            );
                          })
                        ) : (
                          <p className="text-sm text-muted-foreground">Нет прикрепленных файлов</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </DialogContent>
            </Dialog>

            {/* Диалог редактирования плана */}
            <Dialog open={editDialogOpen} onOpenChange={(open) => {
              setEditDialogOpen(open);
              if (!open) {
                setSelectedPlan(null);
                setSelectedFiles([]);
              }
            }}>
              <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>Редактировать план занятий</DialogTitle>
                </DialogHeader>
                {selectedPlan && (
                  <div className="space-y-4">
                    {(selectedPlan.status === 'sent' || selectedPlan.status === 'archived') && (
                      <div className="p-3 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-md">
                        <p className="text-sm text-amber-800 dark:text-amber-200 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4" />
                          Этот план уже отправлен студенту и не может быть изменен
                        </p>
                      </div>
                    )}
                    <div>
                      <Label>Название плана *</Label>
                      <Input
                        value={formData.title}
                        onChange={(e) => setFormData({...formData, title: e.target.value})}
                        placeholder="Например: Неделя 1: Алгебра"
                        disabled={selectedPlan.status === 'sent' || selectedPlan.status === 'archived'}
                      />
                    </div>
                    <div>
                      <Label>Дата начала недели *</Label>
                      <Input
                        type="date"
                        value={formData.week_start_date}
                        onChange={(e) => setFormData({...formData, week_start_date: e.target.value})}
                        required
                        disabled={selectedPlan.status === 'sent' || selectedPlan.status === 'archived'}
                      />
                    </div>
                    <div>
                      <Label>Содержание плана *</Label>
                      <Textarea
                        value={formData.content}
                        onChange={(e) => setFormData({...formData, content: e.target.value})}
                        placeholder="Опишите план занятий на неделю..."
                        rows={10}
                        disabled={selectedPlan.status === 'sent' || selectedPlan.status === 'archived'}
                      />
                    </div>
                    <div>
                      <Label>Статус</Label>
                      <Select
                        value={formData.status}
                        onValueChange={(value) => setFormData({...formData, status: value as 'draft' | 'sent'})}
                        disabled={selectedPlan.status === 'sent' || selectedPlan.status === 'archived'}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="draft">Черновик</SelectItem>
                          <SelectItem value="sent">Отправить сразу</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Прикрепленные файлы</Label>
                      {(selectedPlan.status === 'sent' || selectedPlan.status === 'archived') && (
                        <p className="text-xs text-amber-600 dark:text-amber-500 mt-1 flex items-center gap-1">
                          <AlertCircle className="w-3 h-3" />
                          Нельзя изменять файлы в отправленных или архивных планах
                        </p>
                      )}
                      <div className="mt-2 space-y-2">
                        {selectedPlan.files && selectedPlan.files.length > 0 ? (
                          selectedPlan.files.map((file) => {
                            const FileIcon = getFileIcon(file.name);
                            const iconColor = getFileIconColor(file.name);
                            const canDelete = selectedPlan.status === 'draft';

                            return (
                              <div key={file.id} className="flex items-center justify-between p-3 bg-muted rounded-md hover:bg-muted/80 transition-colors">
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                  <FileIcon className={`w-4 h-4 flex-shrink-0 ${iconColor}`} />
                                  <a
                                    href={file.file_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sm font-medium hover:underline truncate"
                                    onClick={(e) => handleProtectedFileClick(e, file.file_url, file.name)}
                                  >
                                    {file.name}
                                  </a>
                                  <span className="text-xs text-muted-foreground whitespace-nowrap flex-shrink-0">
                                    {formatFileSize(file.file_size)}
                                  </span>
                                </div>
                                {canDelete && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleDeleteFile(selectedPlan.id, file.id)}
                                    disabled={deletingFile === file.id}
                                    className="flex-shrink-0"
                                  >
                                    {deletingFile === file.id ? (
                                      <span className="text-xs">Удаление...</span>
                                    ) : (
                                      <Trash2 className="w-4 h-4 text-destructive" />
                                    )}
                                  </Button>
                                )}
                              </div>
                            );
                          })
                        ) : (
                          <p className="text-sm text-muted-foreground">Нет прикрепленных файлов</p>
                        )}
                      </div>
                    </div>
                    {selectedPlan.status === 'draft' && (
                      <div>
                        <Label>Загрузить файл</Label>
                        <div className="mt-2 space-y-2">
                          <Input
                            type="file"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) {
                                handleUploadFile(selectedPlan.id, file);
                                e.target.value = '';
                              }
                            }}
                            disabled={uploadingFile === selectedPlan.id}
                            accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.zip,.rar"
                          />
                          <p className="text-xs text-muted-foreground flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" />
                            Максимальный размер файла: 10 MB
                          </p>
                          {uploadingFile === selectedPlan.id && (
                            <p className="text-xs text-muted-foreground mt-1">Загрузка...</p>
                          )}
                        </div>
                      </div>
                    )}
                    <div className="flex justify-end gap-2">
                      <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                        {selectedPlan.status === 'sent' || selectedPlan.status === 'archived' ? 'Закрыть' : 'Отмена'}
                      </Button>
                      {(selectedPlan.status === 'draft') && (
                        <Button onClick={handleEditPlan}>
                          Сохранить
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </DialogContent>
            </Dialog>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}

