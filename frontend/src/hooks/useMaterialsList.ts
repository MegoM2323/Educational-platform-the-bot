import { useQuery, UseQueryResult } from "@tanstack/react-query";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";
import { logger } from "@/utils/logger";

export interface Material {
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

export interface Subject {
  id: number;
  name: string;
  description: string;
  color: string;
}

export interface UseMaterialsListResult {
  materials: Material[];
  subjects: Subject[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Hook to fetch and cache materials list using React Query
 * Provides automatic caching, background refetching, and stale data management
 * Cache TTL: 5 minutes
 */
export const useMaterialsList = (): UseQueryResult<
  {
    materials: Material[];
    subjects: Subject[];
  },
  Error
> => {
  return useQuery({
    queryKey: ["materials-list"],
    queryFn: async () => {
      try {
        const materialsResponse = await apiClient.request<any>(
          "/materials/student/"
        );
        const subjectsResponse = await apiClient.request<Subject[]>(
          "/materials/subjects/"
        );

        if (!materialsResponse.data) {
          throw new Error(
            materialsResponse.error || "Ошибка загрузки материалов"
          );
        }

        const materialsBySubject = materialsResponse.data.materials_by_subject || {};
        const allMaterials: Material[] = [];

        for (const subjectData of Object.values(materialsBySubject)) {
          const subjectMaterials = (subjectData as any).materials || [];
          allMaterials.push(...subjectMaterials);
        }

        return {
          materials: allMaterials,
          subjects: subjectsResponse.data || [],
        };
      } catch (err: unknown) {
        logger.error("Materials fetch error:", err);
        throw err;
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
};

/**
 * Hook for fetching a single material with caching
 */
export const useMaterial = (materialId: number) => {
  return useQuery({
    queryKey: ["material", materialId],
    queryFn: async () => {
      const response = await apiClient.request<Material>(
        `/materials/${materialId}/`
      );

      if (!response.data) {
        throw new Error("Материал не найден");
      }

      return response.data;
    },
    enabled: !!materialId,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
};

/**
 * Hook for updating material progress with optimistic updates
 */
export const useUpdateMaterialProgress = () => {
  return async (materialId: number, progressPercentage: number) => {
    try {
      const response = await apiClient.request(
        `/materials/${materialId}/progress/`,
        {
          method: "POST",
          body: JSON.stringify({
            progress_percentage: progressPercentage,
            time_spent: 1,
          }),
        }
      );

      if (!response.data) {
        throw new Error("Ошибка при обновлении прогресса");
      }

      return response.data;
    } catch (err: unknown) {
      logger.error("Progress update error:", err);
      throw err;
    }
  };
};
