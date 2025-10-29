import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { BookOpen, Search, Download, Eye, Filter, Clock, User, FileText, Video, Presentation, TestTube, Home, Send, MessageSquare } from "lucide-react";
import { useState, useEffect } from "react";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";
import { useToast } from "@/hooks/use-toast";
import { useErrorNotification, useSuccessNotification } from "@/components/NotificationSystem";
import { ErrorState, EmptyState } from "@/components/LoadingStates";
import MaterialSubmissionForm from "@/components/forms/MaterialSubmissionForm";
import MaterialSubmissionStatus from "@/components/MaterialSubmissionStatus";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { StudentSidebar } from "@/components/layout/StudentSidebar";

// Интерфейсы для данных
interface Material {
  id: number;
  title: string;
  description: string;
  content: string;
  author: number;
  author_name: string;
  subject: number;
  subject_name: string;
  type: 'lesson' | 'presentation' | 'video' | 'document' | 'test' | 'homework';
  status: 'draft' | 'active' | 'archived';
  is_public: boolean;
  file?: string;
  video_url?: string;
  tags: string;
  difficulty_level: number;
  created_at: string;
  published_at?: string;
  progress?: {
    is_completed: boolean;
    progress_percentage: number;
    time_spent: number;
    started_at?: string;
    completed_at?: string;
    last_accessed?: string;
  };
}

interface Subject {
  id: number;
  name: string;
  description: string;
  color: string;
}

const typeIcons = {
  lesson: BookOpen,
  presentation: Presentation,
  video: Video,
  document: FileText,
  test: TestTube,
  homework: Home,
};

const typeLabels = {
  lesson: 'Урок',
  presentation: 'Презентация',
  video: 'Видео',
  document: 'Документ',
  test: 'Тест',
  homework: 'Домашнее задание',
};

export default function StudentMaterials() {
  const { toast } = useToast();
  const showError = useErrorNotification();
  const showSuccess = useSuccessNotification();
  
  const [materials, setMaterials] = useState<Material[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSubject, setSelectedSubject] = useState<string>("all");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("all");
  const [submissionDialogOpen, setSubmissionDialogOpen] = useState(false);
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState<Material | null>(null);

  // Загрузка материалов
  const fetchMaterials = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      if (selectedSubject !== "all") params.append('subject_id', selectedSubject);
      if (selectedType !== "all") params.append('type', selectedType);
      if (selectedDifficulty !== "all") params.append('difficulty', selectedDifficulty);
      
      const response = await apiClient.request<any>(`/materials/student/?${params.toString()}`);
      
      if (response.data) {
        // Извлекаем материалы из materials_by_subject
        const materialsBySubject = response.data.materials_by_subject || {};
        const allMaterials: Material[] = [];
        
        for (const subjectData of Object.values(materialsBySubject)) {
          const subjectMaterials = (subjectData as any).materials || [];
          allMaterials.push(...subjectMaterials);
        }
        
        setMaterials(allMaterials);
      } else {
        const errorMessage = response.error || 'Ошибка загрузки материалов';
        setError(errorMessage);
        showError(errorMessage);
      }
    } catch (err: any) {
      const errorMessage = 'Произошла ошибка при загрузке материалов';
      setError(errorMessage);
      showError(errorMessage);
      console.error('Materials fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Загрузка предметов
  const fetchSubjects = async () => {
    try {
      const response = await apiClient.request<Subject[]>('/materials/subjects/');
      if (response.data) {
        setSubjects(response.data);
      }
    } catch (err) {
      console.error('Subjects fetch error:', err);
    }
  };

  useEffect(() => {
    fetchMaterials();
    fetchSubjects();
  }, [selectedSubject, selectedType, selectedDifficulty]);

  // Фильтрация по поисковому запросу
  const filteredMaterials = materials.filter(material =>
    material.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    material.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    material.subject_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    material.author_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Скачивание файла
  const handleDownload = async (material: Material) => {
    try {
      if (!material.file) {
        showError('Файл не найден');
        return;
      }

      const response = await fetch(`/api/materials/materials/${material.id}/download/`, {
        headers: {
          'Authorization': `Token ${localStorage.getItem('authToken') || ''}`,
        },
      });

      if (!response.ok) {
        throw new Error('Ошибка скачивания файла');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = material.file.split('/').pop() || 'material';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      showSuccess('Файл успешно скачан');
    } catch (err: any) {
      showError('Ошибка при скачивании файла');
      console.error('Download error:', err);
    }
  };

  // Обновление прогресса
  const updateProgress = async (materialId: number, progressPercentage: number) => {
    try {
      await apiClient.request(`/materials/${materialId}/progress/`, {
        method: 'POST',
        body: JSON.stringify({
          progress_percentage: progressPercentage,
          time_spent: 1,
        }),
      });
      
      // Обновляем локальное состояние
      setMaterials(prev => prev.map(material => 
        material.id === materialId 
          ? {
              ...material,
              progress: {
                ...material.progress,
                progress_percentage: progressPercentage,
                is_completed: progressPercentage >= 100,
                time_spent: (material.progress?.time_spent || 0) + 1,
              }
            }
          : material
      ));
    } catch (err) {
      console.error('Progress update error:', err);
    }
  };

  const getTypeIcon = (type: string) => {
    const IconComponent = typeIcons[type as keyof typeof typeIcons] || BookOpen;
    return <IconComponent className="w-5 h-5" />;
  };

  const getDifficultyColor = (level: number) => {
    if (level <= 2) return "bg-green-100 text-green-800";
    if (level <= 3) return "bg-yellow-100 text-yellow-800";
    return "bg-red-100 text-red-800";
  };

  // Функции для работы с диалогами
  const handleOpenSubmissionDialog = (material: Material) => {
    setSelectedMaterial(material);
    setSubmissionDialogOpen(true);
  };

  const handleOpenStatusDialog = (material: Material) => {
    setSelectedMaterial(material);
    setStatusDialogOpen(true);
  };

  const handleSubmissionSuccess = () => {
    setSubmissionDialogOpen(false);
    setSelectedMaterial(null);
    fetchMaterials(); // Обновляем список материалов
  };

  const handleSubmissionCancel = () => {
    setSubmissionDialogOpen(false);
    setSelectedMaterial(null);
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <StudentSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <button aria-label="Toggle Sidebar" className="rounded border px-2 py-1 text-xs">
              Меню
            </button>
            <div className="flex-1" />
          </header>
          <main className="p-6">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold">Учебные материалы</h1>
                  <p className="text-muted-foreground">Все материалы от ваших преподавателей</p>
                </div>
              </div>

      {/* Search and Filter */}
      <Card className="p-4">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input 
              placeholder="Поиск материалов..." 
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <Select value={selectedSubject} onValueChange={setSelectedSubject}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Предмет" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все предметы</SelectItem>
                {Array.isArray(subjects) && subjects.map(subject => (
                  <SelectItem key={subject.id} value={subject.id.toString()}>
                    {subject.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            <Select value={selectedType} onValueChange={setSelectedType}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Тип" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все типы</SelectItem>
                {Object.entries(typeLabels).map(([key, label]) => (
                  <SelectItem key={key} value={key}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            <Select value={selectedDifficulty} onValueChange={setSelectedDifficulty}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Сложность" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все уровни</SelectItem>
                {[1, 2, 3, 4, 5].map(level => (
                  <SelectItem key={level} value={level.toString()}>
                    Уровень {level}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      {/* Обработка ошибок */}
      {error && (
        <ErrorState 
          error={error}
          onRetry={fetchMaterials}
        />
      )}

      {/* Загрузка */}
      {loading && (
        <div className="grid md:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="p-6">
              <div className="flex items-start gap-4">
                <Skeleton className="w-12 h-12 rounded-lg" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-8 w-24" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Materials Grid */}
      {!loading && !error && (
        <div className="grid md:grid-cols-2 gap-6">
          {filteredMaterials.map((material) => (
            <Card key={material.id} className="p-6 hover:border-primary transition-colors">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 gradient-primary rounded-lg flex items-center justify-center flex-shrink-0">
                  {getTypeIcon(material.type)}
                </div>
                <div className="flex-1">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-bold mb-1">{material.title}</h3>
                      <p className="text-sm text-muted-foreground flex items-center gap-1">
                        <User className="w-3 h-3" />
                        {material.author_name}
                      </p>
                    </div>
                    <div className="flex flex-col gap-2">
                      <Badge variant={material.progress?.is_completed ? "default" : "secondary"}>
                        {material.progress?.is_completed ? "Завершено" : "В процессе"}
                      </Badge>
                      <Badge className={getDifficultyColor(material.difficulty_level)}>
                        Уровень {material.difficulty_level}
                      </Badge>
                    </div>
                  </div>
                  
                  <p className="text-sm text-muted-foreground mb-2">{material.description}</p>
                  
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
                    <span className="font-medium">{material.subject_name}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      {getTypeIcon(material.type)}
                      {typeLabels[material.type as keyof typeof typeLabels]}
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(material.created_at).toLocaleDateString('ru-RU')}
                    </span>
                  </div>

                  {/* Progress Bar */}
                  {material.progress && (
                    <div className="mb-4">
                      <div className="flex justify-between text-xs text-muted-foreground mb-1">
                        <span>Прогресс изучения</span>
                        <span>{material.progress.progress_percentage}%</span>
                      </div>
                      <Progress value={material.progress.progress_percentage} className="h-2" />
                      {material.progress.time_spent > 0 && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Время изучения: {material.progress.time_spent} мин
                        </p>
                      )}
                    </div>
                  )}

                  <div className="flex gap-2">
                    <Button 
                      size="sm" 
                      className="flex-1"
                      onClick={() => updateProgress(material.id, Math.min((material.progress?.progress_percentage || 0) + 25, 100))}
                    >
                      <Eye className="w-4 h-4 mr-2" />
                      Изучить
                    </Button>
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => handleOpenSubmissionDialog(material)}
                    >
                      <Send className="w-4 h-4 mr-1" />
                      Ответить
                    </Button>
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => handleOpenStatusDialog(material)}
                    >
                      <MessageSquare className="w-4 h-4" />
                    </Button>
                    {material.file && (
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => handleDownload(material)}
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                    )}
                    {material.video_url && (
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => window.open(material.video_url, '_blank')}
                      >
                        <Video className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredMaterials.length === 0 && (
        <EmptyState
          title="Материалы не найдены"
          description={searchQuery || selectedSubject !== "all" || selectedType !== "all" || selectedDifficulty !== "all" 
            ? "Попробуйте изменить фильтры поиска"
            : "Пока нет доступных материалов. Обратитесь к преподавателю."
          }
          icon={<BookOpen className="w-8 h-8 text-muted-foreground" />}
        />
      )}

      {/* Диалог отправки ответа */}
      <Dialog open={submissionDialogOpen} onOpenChange={setSubmissionDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Отправить ответ на материал</DialogTitle>
          </DialogHeader>
          {selectedMaterial && (
            <MaterialSubmissionForm
              materialId={selectedMaterial.id}
              materialTitle={selectedMaterial.title}
              onSuccess={handleSubmissionSuccess}
              onCancel={handleSubmissionCancel}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Диалог статуса ответа */}
      <Dialog open={statusDialogOpen} onOpenChange={setStatusDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Статус ответа</DialogTitle>
          </DialogHeader>
          {selectedMaterial && (
            <MaterialSubmissionStatus
              materialId={selectedMaterial.id}
              materialTitle={selectedMaterial.title}
              onEditSubmission={() => {
                setStatusDialogOpen(false);
                handleOpenSubmissionDialog(selectedMaterial);
              }}
            />
          )}
        </DialogContent>
      </Dialog>
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
