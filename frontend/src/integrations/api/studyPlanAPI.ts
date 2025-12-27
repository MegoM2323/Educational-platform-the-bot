import { unifiedAPI } from './unifiedClient';

/**
 * Study Plan Generation API Client
 *
 * Provides methods for generating personalized study plans using AI:
 * - Problem sets with A/B/C difficulty levels
 * - Reference guides with theory explanations
 * - Video playlists with curated educational content
 * - Weekly study plans with structured timeline
 */

// Request Types
export interface StudyPlanParams {
  student_id: number;
  subject_id: number;
  grade: number;
  topic: string;
  subtopics: string;
  goal: string;
  task_counts?: { A: number; B: number; C: number };
  constraints?: string;
  reference_level?: string;
  examples_count?: string;
  video_duration?: string;
  video_language?: string;
}

// Response Types
export interface GeneratedFile {
  type: 'problem_set' | 'reference_guide' | 'video_list' | 'weekly_plan';
  url: string;
  filename?: string;
}

export interface GenerationResponse {
  success: boolean;
  generation_id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress_message?: string;
  files?: GeneratedFile[];
  error?: string;
  error_message?: string;
  created_at?: string;
  updated_at?: string;
  completed_at?: string;
}

export interface StudyPlanGeneration {
  id: number;
  student_id: number;
  subject_id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  request_params: StudyPlanParams;
  files: GeneratedFile[];
  error_message?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Study Plan API Methods
 */
export const studyPlanAPI = {
  /**
   * Инициирует генерацию учебного плана
   *
   * @param params - Параметры генерации (предмет, класс, тема, цели и т.д.)
   * @returns Promise с generation_id для отслеживания статуса
   * @throws Error если запрос не удался
   */
  generateStudyPlan: async (params: StudyPlanParams): Promise<GenerationResponse> => {
    const response = await unifiedAPI.post<GenerationResponse>(
      '/materials/study-plan/generate/',
      params
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data as GenerationResponse;
  },

  /**
   * Получает статус генерации учебного плана
   *
   * Используется для polling: вызывается периодически до получения статуса 'completed' или 'failed'
   *
   * @param generationId - ID генерации, полученный из generateStudyPlan()
   * @returns Promise со статусом и файлами (если завершено)
   * @throws Error если запрос не удался
   */
  getGenerationStatus: async (generationId: number): Promise<GenerationResponse> => {
    const response = await unifiedAPI.get<GenerationResponse>(
      `/materials/study-plan/generation/${generationId}/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data as GenerationResponse;
  },

  /**
   * Получает список сгенерированных файлов
   *
   * @param generationId - ID завершённой генерации
   * @returns Promise с массивом файлов (problem_set, reference_guide, video_list, weekly_plan)
   * @throws Error если генерация не завершена или не найдена
   */
  getGeneratedFiles: async (generationId: number): Promise<GeneratedFile[]> => {
    const response = await unifiedAPI.get<GeneratedFile[]>(
      `/materials/study-plan/generation/${generationId}/files/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data as GeneratedFile[];
  },

  /**
   * Получает полную информацию о генерации (включая параметры запроса)
   *
   * @param generationId - ID генерации
   * @returns Promise с полными данными генерации
   * @throws Error если генерация не найдена
   */
  getGeneration: async (generationId: number): Promise<StudyPlanGeneration> => {
    const response = await unifiedAPI.get<StudyPlanGeneration>(
      `/materials/study-plan/generation/${generationId}/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data as StudyPlanGeneration;
  },

  /**
   * Получает список всех генераций для текущего пользователя
   *
   * @param filters - Опциональные фильтры (student_id, subject_id, status)
   * @returns Promise с массивом генераций
   * @throws Error если запрос не удался
   */
  listGenerations: async (filters?: {
    student_id?: number;
    subject_id?: number;
    status?: 'pending' | 'processing' | 'completed' | 'failed';
  }): Promise<StudyPlanGeneration[]> => {
    const response = await unifiedAPI.get<StudyPlanGeneration[]>(
      '/materials/study-plan/generations/',
      { params: filters }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data as StudyPlanGeneration[];
  },

  /**
   * Отменяет активную генерацию
   *
   * @param generationId - ID генерации для отмены
   * @returns Promise с обновлённым статусом
   * @throws Error если генерация уже завершена или не найдена
   */
  cancelGeneration: async (generationId: number): Promise<GenerationResponse> => {
    const response = await unifiedAPI.post<GenerationResponse>(
      `/materials/study-plan/generation/${generationId}/cancel/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data as GenerationResponse;
  }
};
