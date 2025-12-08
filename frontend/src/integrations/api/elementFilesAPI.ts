/**
 * Element Files API Client
 * Управление файлами для элементов графа знаний
 */

import { unifiedAPI } from './unifiedClient';

export interface ElementFile {
  id: number;
  original_filename: string;
  file_size: number;
  uploaded_at: string;
  file_url: string;
}

export interface ElementFilesResponse {
  success: boolean;
  data: ElementFile[];
  count?: number;
}

export const elementFilesAPI = {
  /**
   * Получить список всех файлов элемента
   */
  listFiles: async (elementId: number): Promise<ElementFile[]> => {
    const response = await unifiedAPI.get<ElementFilesResponse>(
      `/knowledge-graph/elements/${elementId}/files/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return (response.data as ElementFilesResponse).data || [];
  },

  /**
   * Загрузить новый файл к элементу
   */
  uploadFile: async (elementId: number, file: File): Promise<ElementFile> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await unifiedAPI.post<{ success: boolean; data: ElementFile }>(
      `/knowledge-graph/elements/${elementId}/files/`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return (response.data as { success: boolean; data: ElementFile }).data;
  },

  /**
   * Удалить файл элемента
   */
  deleteFile: async (elementId: number, fileId: number): Promise<void> => {
    const response = await unifiedAPI.delete<{ success: boolean }>(
      `/knowledge-graph/elements/${elementId}/files/${fileId}/`
    );

    if (response.error) {
      throw new Error(response.error);
    }
  },
};
