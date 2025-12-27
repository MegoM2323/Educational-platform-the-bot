import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  BookOpen,
  Search,
  Filter,
  Clock,
  User,
  FileText,
  Video,
  Presentation,
  TestTube,
  Home,
  Send,
  MessageSquare,
  Download,
  Eye,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useToast } from "@/hooks/useToast";
import {
  useErrorNotification,
  useSuccessNotification,
} from "@/components/NotificationSystem";
import { ErrorState, EmptyState } from "@/components/LoadingStates";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { MaterialListItem } from "@/components/MaterialListItem";
import MaterialSubmissionForm from "@/components/forms/MaterialSubmissionForm";
import MaterialSubmissionStatus from "@/components/MaterialSubmissionStatus";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";
import { logger } from "@/utils/logger";
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import { handleProtectedFileClick } from "@/utils/fileDownload";

interface Material {
  id: number;
  title: string;
  description: string;
  content: string;
  author: number;
  author_name: string;
  subject: number;
  subject_name: string;
  type: "lesson" | "presentation" | "video" | "document" | "test" | "homework";
  status: "draft" | "active" | "archived";
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

type SortKey = "title" | "date" | "difficulty";

const ITEMS_PER_PAGE = 20;
const INITIAL_DISPLAY = 10;

// Простая функция debounce без внешних зависимостей
function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout | null = null;
  
  return (...args: Parameters<T>) => {
    if (timeoutId) clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
      func(...args);
    }, delay);
  };
}

export default function MaterialsList() {
  const { toast } = useToast();
  const showError = useErrorNotification();
  const showSuccess = useSuccessNotification();

  // Основное состояние
  const [materials, setMaterials] = useState<Material[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Состояние фильтров (локальное)
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSubject, setSelectedSubject] = useState<string>("all");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("all");
  const [sortBy, setSortBy] = useState<SortKey>("date");

  // Состояние пагинации
  const [currentPage, setCurrentPage] = useState(1);
  const [displayCount, setDisplayCount] = useState(INITIAL_DISPLAY);

  // Состояние диалогов
  const [submissionDialogOpen, setSubmissionDialogOpen] = useState(false);
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState<Material | null>(null);

  // Загрузка материалов (только один раз при монтировании)
  useEffect(() => {
    fetchMaterials();
    fetchSubjects();
  }, []);

  const fetchMaterials = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.request<any>("/materials/student/");

      if (response.data) {
        const materialsBySubject = response.data.materials_by_subject || {};
        const allMaterials: Material[] = [];

        for (const subjectData of Object.values(materialsBySubject)) {
          const subjectMaterials = (subjectData as any).materials || [];
          allMaterials.push(...subjectMaterials);
        }

        setMaterials(allMaterials);
      } else {
        const errorMessage = response.error || "Ошибка загрузки материалов";
        setError(errorMessage);
        showError(errorMessage);
      }
    } catch (err: unknown) {
      const errorMessage = "Произошла ошибка при загрузке материалов";
      setError(errorMessage);
      showError(errorMessage);
      logger.error("Materials fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSubjects = async () => {
    try {
      const response = await apiClient.request<Subject[]>(
        "/materials/subjects/"
      );
      if (response.data) {
        setSubjects(response.data);
      }
    } catch (err) {
      logger.error("Subjects fetch error:", err);
    }
  };

  // Фильтрация (мемоизированная)
  const filteredMaterials = useMemo(() => {
    return materials.filter((material) => {
      const matchesSearch =
        material.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        material.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        material.subject_name
          .toLowerCase()
          .includes(searchQuery.toLowerCase()) ||
        material.author_name.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesSubject =
        selectedSubject === "all" || material.subject_name === selectedSubject;
      const matchesType =
        selectedType === "all" || material.type === selectedType;
      const matchesDifficulty =
        selectedDifficulty === "all" ||
        material.difficulty_level === parseInt(selectedDifficulty);

      return (
        matchesSearch &&
        matchesSubject &&
        matchesType &&
        matchesDifficulty
      );
    });
  }, [materials, searchQuery, selectedSubject, selectedType, selectedDifficulty]);

  // Сортировка (мемоизированная)
  const sortedMaterials = useMemo(() => {
    const sorted = [...filteredMaterials];

    switch (sortBy) {
      case "title":
        sorted.sort((a, b) => a.title.localeCompare(b.title));
        break;
      case "date":
        sorted.sort(
          (a, b) =>
            new Date(b.created_at).getTime() -
            new Date(a.created_at).getTime()
        );
        break;
      case "difficulty":
        sorted.sort((a, b) => b.difficulty_level - a.difficulty_level);
        break;
    }

    return sorted;
  }, [filteredMaterials, sortBy]);

  // Пагинация (мемоизированная)
  const paginatedMaterials = useMemo(() => {
    const startIdx = (currentPage - 1) * ITEMS_PER_PAGE;
    return sortedMaterials.slice(startIdx, startIdx + ITEMS_PER_PAGE);
  }, [sortedMaterials, currentPage]);

  const totalPages = Math.ceil(sortedMaterials.length / ITEMS_PER_PAGE);

  // Debounced search handler
  const handleSearchChange = useCallback(
    debounce((value: string) => {
      setSearchQuery(value);
      setCurrentPage(1);
    }, 300),
    []
  );

  // Обновление прогресса
  const updateProgress = async (
    materialId: number,
    progressPercentage: number
  ) => {
    try {
      await apiClient.request(`/materials/${materialId}/progress/`, {
        method: "POST",
        body: JSON.stringify({
          progress_percentage: progressPercentage,
          time_spent: 1,
        }),
      });

      // Обновляем локальное состояние
      setMaterials((prev) =>
        prev.map((material) =>
          material.id === materialId
            ? {
                ...material,
                progress: {
                  ...material.progress,
                  progress_percentage: progressPercentage,
                  is_completed: progressPercentage >= 100,
                  time_spent: (material.progress?.time_spent || 0) + 1,
                },
              }
            : material
        )
      );
    } catch (err) {
      logger.error("Progress update error:", err);
      showError("Ошибка при обновлении прогресса");
    }
  };

  // Скачивание файла
  const handleDownload = async (material: Material) => {
    try {
      if (!material.file) {
        showError("Файл не найден");
        return;
      }

      const response = await fetch(
        `/api/materials/materials/${material.id}/download/`,
        {
          headers: {
            Authorization: `Token ${localStorage.getItem("authToken") || ""}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Ошибка скачивания файла");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = material.file.split("/").pop() || "material";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      showSuccess("Файл успешно скачан");
    } catch (err: unknown) {
      showError("Ошибка при скачивании файла");
      logger.error("Download error:", err);
    }
  };

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
    fetchMaterials();
  };

  const handleSubmissionCancel = () => {
    setSubmissionDialogOpen(false);
    setSelectedMaterial(null);
  };

  return (
    <ErrorBoundary>
      <SidebarProvider>
        <div className="flex min-h-screen w-full">
          <StudentSidebar />
          <SidebarInset>
            <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
              <SidebarTrigger />
              <div className="flex-1" />
            </header>

            <main className="p-6">
              <div className="space-y-6">
                {/* Заголовок */}
                <div className="flex items-center justify-between">
                  <div>
                    <h1 className="text-3xl font-bold">Учебные материалы</h1>
                    <p className="text-muted-foreground">
                      Всего материалов: {sortedMaterials.length}
                    </p>
                  </div>
                </div>

                {/* Фильтры и поиск */}
                <Card className="p-4">
                  <div className="space-y-4">
                    {/* Поиск */}
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        placeholder="Поиск материалов (с задержкой 300ms)..."
                        className="pl-10"
                        onChange={(e) => handleSearchChange(e.target.value)}
                        defaultValue={searchQuery}
                      />
                    </div>

                    {/* Селекторы */}
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                      <Select value={selectedSubject} onValueChange={(value) => {
                        setSelectedSubject(value);
                        setCurrentPage(1);
                      }}>
                        <SelectTrigger>
                          <SelectValue placeholder="Предмет" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Все предметы</SelectItem>
                          {subjects.map((subject) => (
                            <SelectItem key={subject.id} value={subject.name}>
                              {subject.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      <Select value={selectedType} onValueChange={(value) => {
                        setSelectedType(value);
                        setCurrentPage(1);
                      }}>
                        <SelectTrigger>
                          <SelectValue placeholder="Тип" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Все типы</SelectItem>
                          <SelectItem value="lesson">Урок</SelectItem>
                          <SelectItem value="presentation">Презентация</SelectItem>
                          <SelectItem value="video">Видео</SelectItem>
                          <SelectItem value="document">Документ</SelectItem>
                          <SelectItem value="test">Тест</SelectItem>
                          <SelectItem value="homework">Домашнее задание</SelectItem>
                        </SelectContent>
                      </Select>

                      <Select value={selectedDifficulty} onValueChange={(value) => {
                        setSelectedDifficulty(value);
                        setCurrentPage(1);
                      }}>
                        <SelectTrigger>
                          <SelectValue placeholder="Сложность" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Все уровни</SelectItem>
                          {[1, 2, 3, 4, 5].map((level) => (
                            <SelectItem key={level} value={level.toString()}>
                              Уровень {level}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      <Select value={sortBy} onValueChange={(value) => setSortBy(value as SortKey)}>
                        <SelectTrigger>
                          <SelectValue placeholder="Сортировка" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="date">По дате</SelectItem>
                          <SelectItem value="title">По названию</SelectItem>
                          <SelectItem value="difficulty">По сложности</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </Card>

                {/* Обработка ошибок */}
                {error && <ErrorState error={error} onRetry={fetchMaterials} />}

                {/* Скелетоны загрузки */}
                {loading && (
                  <div className="grid gap-6">
                    {[...Array(5)].map((_, i) => (
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

                {/* Список материалов */}
                {!loading && !error && (
                  <>
                    <div className="grid gap-6">
                      {paginatedMaterials.map((material) => (
                        <MaterialListItem
                          key={material.id}
                          material={material}
                          index={materials.indexOf(material)}
                          onView={(m) => {
                            updateProgress(
                              m.id,
                              Math.min(
                                (m.progress?.progress_percentage || 0) + 25,
                                100
                              )
                            );
                          }}
                          onSubmit={handleOpenSubmissionDialog}
                          onStatus={handleOpenStatusDialog}
                          onDownload={handleDownload}
                          onProgress={updateProgress}
                        />
                      ))}
                    </div>

                    {/* Пагинация */}
                    {totalPages > 1 && (
                      <Card className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="text-sm text-muted-foreground">
                            Страница {currentPage} из {totalPages}
                          </div>
                          <div className="flex gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() =>
                                setCurrentPage((p) => Math.max(1, p - 1))
                              }
                              disabled={currentPage === 1}
                            >
                              <ChevronUp className="w-4 h-4" />
                              Предыдущая
                            </Button>

                            <div className="flex gap-1">
                              {Array.from({ length: Math.min(5, totalPages) }).map(
                                (_, i) => {
                                  const pageNum = i + 1;
                                  return (
                                    <Button
                                      key={pageNum}
                                      variant={
                                        currentPage === pageNum
                                          ? "default"
                                          : "outline"
                                      }
                                      size="sm"
                                      onClick={() => setCurrentPage(pageNum)}
                                      className="w-8 h-8 p-0"
                                    >
                                      {pageNum}
                                    </Button>
                                  );
                                }
                              )}
                            </div>

                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() =>
                                setCurrentPage((p) => Math.min(totalPages, p + 1))
                              }
                              disabled={currentPage === totalPages}
                            >
                              Следующая
                              <ChevronDown className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      </Card>
                    )}
                  </>
                )}

                {/* Пустое состояние */}
                {!loading && !error && paginatedMaterials.length === 0 && (
                  <EmptyState
                    title="Материалы не найдены"
                    description={
                      searchQuery ||
                      selectedSubject !== "all" ||
                      selectedType !== "all" ||
                      selectedDifficulty !== "all"
                        ? "Попробуйте изменить фильтры поиска"
                        : "Пока нет доступных материалов. Обратитесь к преподавателю."
                    }
                    icon={<BookOpen className="w-8 h-8 text-muted-foreground" />}
                  />
                )}
              </div>
            </main>
          </SidebarInset>
        </div>
      </SidebarProvider>

      {/* Диалоги */}
      <Dialog
        open={submissionDialogOpen}
        onOpenChange={setSubmissionDialogOpen}
      >
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
    </ErrorBoundary>
  );
}
