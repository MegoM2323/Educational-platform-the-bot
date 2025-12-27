/**
 * Material Form Validator
 *
 * Comprehensive client-side validation for material creation form.
 * Aligns with backend validation rules from T_MAT_001.
 */

export interface MaterialFormValidationErrors {
  [key: string]: string | string[];
}

export interface MaterialFormValidationResult {
  isValid: boolean;
  errors: MaterialFormValidationErrors;
  errorCount: number;
}

/**
 * Material Form Validation Rules
 * Aligned with backend serializer validation (MaterialCreateSerializer)
 */
export class MaterialFormValidator {
  // Validation constraints
  static readonly TITLE_MIN_LENGTH = 3;
  static readonly TITLE_MAX_LENGTH = 200;
  static readonly DESCRIPTION_MIN_LENGTH = 10;
  static readonly DESCRIPTION_MAX_LENGTH = 5000;
  static readonly CONTENT_MIN_LENGTH = 50;
  static readonly DIFFICULTY_MIN = 1;
  static readonly DIFFICULTY_MAX = 5;
  static readonly FILE_MAX_SIZE_MB = 10;
  static readonly FILE_MAX_SIZE_BYTES = 10 * 1024 * 1024;

  static readonly ALLOWED_FILE_EXTENSIONS = [
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'jpg', 'jpeg', 'png'
  ];

  static readonly VALID_MATERIAL_TYPES = [
    'lesson', 'presentation', 'video', 'document', 'test', 'homework'
  ];

  /**
   * Sanitize text by removing HTML tags
   */
  static sanitizeText(text: string): string {
    if (!text) return '';
    // Remove all HTML tags
    return text.replace(/<[^>]*>/g, '').trim();
  }

  /**
   * Sanitize HTML - allow basic formatting
   */
  static sanitizeHtml(html: string): string {
    if (!html) return '';
    // In a real app, use DOMPurify library for proper sanitization
    // This is a basic implementation
    const tempDiv = document.createElement('div');
    tempDiv.textContent = html;
    return tempDiv.innerHTML;
  }

  /**
   * Validate title field
   */
  static validateTitle(title: string): { valid: boolean; error?: string } {
    if (!title) {
      return { valid: false, error: 'Заголовок обязателен' };
    }

    const sanitized = this.sanitizeText(title);

    if (sanitized.length < this.TITLE_MIN_LENGTH) {
      return {
        valid: false,
        error: `Заголовок должен содержать минимум ${this.TITLE_MIN_LENGTH} символов`
      };
    }

    if (sanitized.length > this.TITLE_MAX_LENGTH) {
      return {
        valid: false,
        error: `Заголовок не может превышать ${this.TITLE_MAX_LENGTH} символов`
      };
    }

    // Check for HTML injection attempts
    if (title !== sanitized) {
      return {
        valid: false,
        error: 'Заголовок не должен содержать HTML-теги'
      };
    }

    return { valid: true };
  }

  /**
   * Validate description field
   */
  static validateDescription(description: string): { valid: boolean; error?: string } {
    if (!description) {
      // Description is optional
      return { valid: true };
    }

    const trimmed = description.trim();

    if (trimmed && trimmed.length > 0 && trimmed.length < this.DESCRIPTION_MIN_LENGTH) {
      return {
        valid: false,
        error: `Описание должно содержать минимум ${this.DESCRIPTION_MIN_LENGTH} символов (если указано)`
      };
    }

    if (trimmed.length > this.DESCRIPTION_MAX_LENGTH) {
      return {
        valid: false,
        error: `Описание не может превышать ${this.DESCRIPTION_MAX_LENGTH} символов`
      };
    }

    return { valid: true };
  }

  /**
   * Validate content field
   * Content is required only if no file and no video are provided
   */
  static validateContent(content: string, hasFile: boolean, hasVideo: boolean):
    { valid: boolean; error?: string } {
    // If no file and no video, content is required with min length
    if (!hasFile && !hasVideo) {
      if (!content || content.trim().length === 0) {
        return {
          valid: false,
          error: 'Укажите содержание, загрузите файл или добавьте ссылку на видео'
        };
      }

      if (content.trim().length < this.CONTENT_MIN_LENGTH) {
        return {
          valid: false,
          error: `Содержание должно содержать минимум ${this.CONTENT_MIN_LENGTH} символов`
        };
      }
    } else {
      // If file or video exists, content is optional
      // But if content is provided, it must meet minimum length
      if (content && content.trim().length > 0 && content.trim().length < this.CONTENT_MIN_LENGTH) {
        return {
          valid: false,
          error: `Содержание должно содержать минимум ${this.CONTENT_MIN_LENGTH} символов (если указано)`
        };
      }
    }

    return { valid: true };
  }

  /**
   * Validate subject field (required)
   */
  static validateSubject(subject: string | number): { valid: boolean; error?: string } {
    if (!subject || (typeof subject === 'string' && subject === '')) {
      return {
        valid: false,
        error: 'Выберите предмет'
      };
    }

    return { valid: true };
  }

  /**
   * Validate content type (required)
   */
  static validateContentType(type: string): { valid: boolean; error?: string } {
    if (!type) {
      return {
        valid: false,
        error: 'Выберите тип материала'
      };
    }

    if (!this.VALID_MATERIAL_TYPES.includes(type)) {
      return {
        valid: false,
        error: `Недопустимый тип материала. Используйте один из: ${this.VALID_MATERIAL_TYPES.join(', ')}`
      };
    }

    return { valid: true };
  }

  /**
   * Validate difficulty level (1-5)
   */
  static validateDifficultyLevel(level: string | number): { valid: boolean; error?: string } {
    const numLevel = typeof level === 'string' ? parseInt(level, 10) : level;

    if (isNaN(numLevel)) {
      return {
        valid: false,
        error: 'Уровень сложности должен быть числом'
      };
    }

    if (numLevel < this.DIFFICULTY_MIN || numLevel > this.DIFFICULTY_MAX) {
      return {
        valid: false,
        error: `Уровень сложности должен быть от ${this.DIFFICULTY_MIN} до ${this.DIFFICULTY_MAX}`
      };
    }

    return { valid: true };
  }

  /**
   * Validate video URL (YouTube, Vimeo, or relative path)
   */
  static validateVideoUrl(url: string): { valid: boolean; error?: string } {
    if (!url) {
      return { valid: true };
    }

    const trimmed = url.trim();

    // Relative path
    if (trimmed.startsWith('/') || trimmed.startsWith('.')) {
      return { valid: true };
    }

    // Full URL
    try {
      const urlObj = new URL(trimmed);

      // Check for supported video hosts or HTTPS
      const supportedHosts = ['youtube.com', 'youtu.be', 'vimeo.com', 'player.vimeo.com'];
      const isYouTube = urlObj.hostname?.includes('youtube.com') || urlObj.hostname?.includes('youtu.be');
      const isVimeo = urlObj.hostname?.includes('vimeo.com');

      if (!isYouTube && !isVimeo) {
        // Allow any HTTPS URL as fallback
        if (urlObj.protocol !== 'https:') {
          return {
            valid: false,
            error: 'URL видео должен использовать HTTPS или быть видео от YouTube/Vimeo'
          };
        }
      }

      return { valid: true };
    } catch {
      return {
        valid: false,
        error: 'URL видео должен быть полным URL (например, https://youtube.com/watch?v=...) или относительным путём (например, /media/videos/...)'
      };
    }
  }

  /**
   * Validate file upload
   */
  static validateFile(file: File | null): { valid: boolean; error?: string } {
    if (!file) {
      return { valid: true };
    }

    // Check file size
    if (file.size > this.FILE_MAX_SIZE_BYTES) {
      return {
        valid: false,
        error: `Размер файла не должен превышать ${this.FILE_MAX_SIZE_MB}MB`
      };
    }

    // Check file extension
    const fileExtension = file.name.split('.').pop()?.toLowerCase();
    if (!fileExtension || !this.ALLOWED_FILE_EXTENSIONS.includes(fileExtension)) {
      return {
        valid: false,
        error: `Неподдерживаемый тип файла. Разрешенные форматы: ${this.ALLOWED_FILE_EXTENSIONS.join(', ')}`
      };
    }

    return { valid: true };
  }

  /**
   * Validate entire form
   */
  static validateForm(data: {
    title: string;
    description: string;
    content: string;
    subject: string | number;
    type: string;
    difficultyLevel: string | number;
    videoUrl: string;
    file: File | null;
  }): MaterialFormValidationResult {
    const errors: MaterialFormValidationErrors = {};

    // Validate required fields
    const titleValidation = this.validateTitle(data.title);
    if (!titleValidation.valid) {
      errors.title = titleValidation.error || 'Ошибка валидации заголовка';
    }

    const subjectValidation = this.validateSubject(data.subject);
    if (!subjectValidation.valid) {
      errors.subject = subjectValidation.error || 'Ошибка валидации предмета';
    }

    const typeValidation = this.validateContentType(data.type);
    if (!typeValidation.valid) {
      errors.type = typeValidation.error || 'Ошибка валидации типа материала';
    }

    // Validate optional fields
    const descriptionValidation = this.validateDescription(data.description);
    if (!descriptionValidation.valid) {
      errors.description = descriptionValidation.error || 'Ошибка валидации описания';
    }

    const contentValidation = this.validateContent(
      data.content,
      !!data.file,
      !!data.videoUrl
    );
    if (!contentValidation.valid) {
      errors.content = contentValidation.error || 'Ошибка валидации содержания';
    }

    const difficultyValidation = this.validateDifficultyLevel(data.difficultyLevel);
    if (!difficultyValidation.valid) {
      errors.difficultyLevel = difficultyValidation.error || 'Ошибка валидации сложности';
    }

    const videoUrlValidation = this.validateVideoUrl(data.videoUrl);
    if (!videoUrlValidation.valid) {
      errors.videoUrl = videoUrlValidation.error || 'Ошибка валидации URL видео';
    }

    const fileValidation = this.validateFile(data.file);
    if (!fileValidation.valid) {
      errors.file = fileValidation.error || 'Ошибка валидации файла';
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors,
      errorCount: Object.keys(errors).length
    };
  }

  /**
   * Validate single field (for real-time validation)
   */
  static validateField(
    fieldName: string,
    value: any,
    context?: any
  ): { valid: boolean; error?: string } {
    switch (fieldName) {
      case 'title':
        return this.validateTitle(value);
      case 'description':
        return this.validateDescription(value);
      case 'content':
        return this.validateContent(
          value,
          context?.hasFile || false,
          context?.hasVideo || false
        );
      case 'subject':
        return this.validateSubject(value);
      case 'type':
        return this.validateContentType(value);
      case 'difficultyLevel':
        return this.validateDifficultyLevel(value);
      case 'videoUrl':
        return this.validateVideoUrl(value);
      case 'file':
        return this.validateFile(value);
      default:
        return { valid: true };
    }
  }
}

/**
 * Hook for real-time field validation with debouncing
 */
export function useFieldValidation(debounceMs: number = 300) {
  const timeoutRef = React.useRef<NodeJS.Timeout>();

  const validateFieldDebounced = (
    fieldName: string,
    value: any,
    context?: any,
    onValidated?: (result: { valid: boolean; error?: string }) => void
  ) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      const result = MaterialFormValidator.validateField(fieldName, value, context);
      onValidated?.(result);
    }, debounceMs);
  };

  const cancelValidation = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
  };

  return { validateFieldDebounced, cancelValidation };
}

import React from 'react';
