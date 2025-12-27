import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { BookOpen } from "lucide-react";
import { useToast } from "@/hooks/useToast";
import {
  useErrorNotification,
  useSuccessNotification,
} from "@/components/NotificationSystem";
import { ErrorState, EmptyState } from "@/components/LoadingStates";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { MaterialListItem } from "@/components/MaterialListItem";
import { MaterialVirtualList } from "@/components/MaterialVirtualList";
import { MaterialListFilters } from "@/components/MaterialListFilters";
import { MaterialListPagination } from "@/components/MaterialListPagination";
import MaterialSubmissionForm from "@/components/forms/MaterialSubmissionForm";
import MaterialSubmissionStatus from "@/components/MaterialSubmissionStatus";
import { useMaterialsList } from "@/hooks/useMaterialsList";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";
import { logger } from "@/utils/logger";
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import { handleProtectedFileClick } from "@/utils/fileDownload";

type SortKey = "title" | "date" | "difficulty";

const ITEMS_PER_PAGE = 20;

// Debounce utility function for search input
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

  // Use React Query hook for caching and automatic refetching
  const { data, isLoading, error, refetch } = useMaterialsList();
  const materials = data?.materials || [];
  const subjects = data?.subjects || [];

  // Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSubject, setSelectedSubject] = useState<string>("all");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("all");
  const [sortBy, setSortBy] = useState<SortKey>("date");

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(ITEMS_PER_PAGE);

  // Dialog state
  const [submissionDialogOpen, setSubmissionDialogOpen] = useState(false);
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState<any | null>(null);

  // Show error notification when query fails
  useEffect(() => {
    if (error) {
      showError("Ошибка загрузки материалов");
      logger.error("Materials fetch error:", error);
    }
  }, [error, showError]);

  // Memoized filtering with support for search, subject, type, difficulty
  const filteredMaterials = useMemo(() => {
    return materials.filter((material) => {
      const searchLower = searchQuery.toLowerCase();
      const matchesSearch =
        material.title.toLowerCase().includes(searchLower) ||
        material.description.toLowerCase().includes(searchLower) ||
        material.subject_name.toLowerCase().includes(searchLower) ||
        material.author_name.toLowerCase().includes(searchLower);

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

  // Memoized sorting
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

  // Memoized pagination
  const paginatedMaterials = useMemo(() => {
    const startIdx = (currentPage - 1) * itemsPerPage;
    return sortedMaterials.slice(startIdx, startIdx + itemsPerPage);
  }, [sortedMaterials, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(sortedMaterials.length / itemsPerPage);

  // Debounced search handler to reduce API calls
  const handleSearchChange = useCallback(
    debounce((value: string) => {
      setSearchQuery(value);
      setCurrentPage(1);
    }, 300),
    []
  );

  // Handle reset of all filters
  const handleResetFilters = useCallback(() => {
    setSearchQuery("");
    setSelectedSubject("all");
    setSelectedType("all");
    setSelectedDifficulty("all");
    setSortBy("date");
    setCurrentPage(1);
  }, []);

  // Update material progress
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

      // Refetch to ensure fresh data
      refetch();
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

  const handleOpenSubmissionDialog = (material: any) => {
    setSelectedMaterial(material);
    setSubmissionDialogOpen(true);
  };

  const handleOpenStatusDialog = (material: any) => {
    setSelectedMaterial(material);
    setStatusDialogOpen(true);
  };

  const handleSubmissionSuccess = () => {
    setSubmissionDialogOpen(false);
    setSelectedMaterial(null);
    refetch();
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

                {/* Filters component with optimized controls */}
                <MaterialListFilters
                  searchQuery={searchQuery}
                  selectedSubject={selectedSubject}
                  selectedType={selectedType}
                  selectedDifficulty={selectedDifficulty}
                  sortBy={sortBy}
                  subjects={subjects}
                  onSearchChange={handleSearchChange}
                  onSubjectChange={(value) => {
                    setSelectedSubject(value);
                    setCurrentPage(1);
                  }}
                  onTypeChange={(value) => {
                    setSelectedType(value);
                    setCurrentPage(1);
                  }}
                  onDifficultyChange={(value) => {
                    setSelectedDifficulty(value);
                    setCurrentPage(1);
                  }}
                  onSortChange={(value) => setSortBy(value as SortKey)}
                  onReset={handleResetFilters}
                  disabled={isLoading}
                />

                {/* Error handling */}
                {error && <ErrorState error={error.message} onRetry={() => refetch()} />}

                {/* Loading state with skeleton items */}
                {isLoading && (
                  <MaterialVirtualList
                    materials={[]}
                    loading={true}
                    onView={() => {}}
                    onSubmit={() => {}}
                    onStatus={() => {}}
                    onDownload={() => {}}
                    onProgress={() => {}}
                  />
                )}

                {/* Main materials list */}
                {!isLoading && !error && paginatedMaterials.length > 0 && (
                  <>
                    {/* Materials grid - using standard grid instead of virtual for pagination */}
                    <div className="grid gap-6">
                      {paginatedMaterials.map((material, index) => (
                        <MaterialListItem
                          key={material.id}
                          material={material}
                          index={index}
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

                    {/* Pagination controls with items per page selector */}
                    {totalPages > 1 && (
                      <MaterialListPagination
                        currentPage={currentPage}
                        totalPages={totalPages}
                        itemsPerPage={itemsPerPage}
                        totalItems={sortedMaterials.length}
                        onPageChange={setCurrentPage}
                        onItemsPerPageChange={setItemsPerPage}
                        disabled={isLoading}
                      />
                    )}
                  </>
                )}

                {/* Empty state when no materials found */}
                {!isLoading &&
                  !error &&
                  paginatedMaterials.length === 0 &&
                  materials.length === 0 && (
                    <EmptyState
                      title="Материалы не найдены"
                      description="Пока нет доступных материалов. Обратитесь к преподавателю."
                      icon={<BookOpen className="w-8 h-8 text-muted-foreground" />}
                    />
                  )}

                {/* Empty state when filters returned no results */}
                {!isLoading &&
                  !error &&
                  paginatedMaterials.length === 0 &&
                  materials.length > 0 && (
                    <EmptyState
                      title="Материалы не найдены"
                      description={
                        searchQuery ||
                        selectedSubject !== "all" ||
                        selectedType !== "all" ||
                        selectedDifficulty !== "all"
                          ? "Попробуйте изменить фильтры поиска"
                          : "Нет материалов для отображения"
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
