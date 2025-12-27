/**
 * Material Form Validator Tests
 * Tests for comprehensive client-side validation
 */

import { MaterialFormValidator } from '../materialFormValidator';

describe('MaterialFormValidator', () => {
  describe('Title Validation', () => {
    it('should reject empty title', () => {
      const result = MaterialFormValidator.validateTitle('');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('обязателен');
    });

    it('should reject title shorter than 3 characters', () => {
      const result = MaterialFormValidator.validateTitle('AB');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('минимум 3');
    });

    it('should reject title longer than 200 characters', () => {
      const longTitle = 'A'.repeat(201);
      const result = MaterialFormValidator.validateTitle(longTitle);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('200');
    });

    it('should reject title with HTML tags', () => {
      const result = MaterialFormValidator.validateTitle('<script>alert("xss")</script>');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('HTML');
    });

    it('should accept valid title', () => {
      const result = MaterialFormValidator.validateTitle('Valid Title');
      expect(result.valid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('should accept title with exactly 3 characters', () => {
      const result = MaterialFormValidator.validateTitle('ABC');
      expect(result.valid).toBe(true);
    });

    it('should accept title with 200 characters', () => {
      const title = 'A'.repeat(200);
      const result = MaterialFormValidator.validateTitle(title);
      expect(result.valid).toBe(true);
    });
  });

  describe('Description Validation', () => {
    it('should accept empty description', () => {
      const result = MaterialFormValidator.validateDescription('');
      expect(result.valid).toBe(true);
    });

    it('should reject description with less than 10 characters when provided', () => {
      const result = MaterialFormValidator.validateDescription('Short');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('минимум 10');
    });

    it('should reject description longer than 5000 characters', () => {
      const longDesc = 'A'.repeat(5001);
      const result = MaterialFormValidator.validateDescription(longDesc);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('5000');
    });

    it('should accept valid description', () => {
      const result = MaterialFormValidator.validateDescription('This is a valid description');
      expect(result.valid).toBe(true);
    });

    it('should accept description with exactly 10 characters', () => {
      const result = MaterialFormValidator.validateDescription('A'.repeat(10));
      expect(result.valid).toBe(true);
    });

    it('should accept description with 5000 characters', () => {
      const desc = 'A'.repeat(5000);
      const result = MaterialFormValidator.validateDescription(desc);
      expect(result.valid).toBe(true);
    });
  });

  describe('Content Validation', () => {
    it('should reject empty content without file or video', () => {
      const result = MaterialFormValidator.validateContent('', false, false);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('содержание');
    });

    it('should accept content with file present', () => {
      const result = MaterialFormValidator.validateContent('', true, false);
      expect(result.valid).toBe(true);
    });

    it('should accept content with video present', () => {
      const result = MaterialFormValidator.validateContent('', false, true);
      expect(result.valid).toBe(true);
    });

    it('should reject content shorter than 50 characters without file/video', () => {
      const result = MaterialFormValidator.validateContent('Short', false, false);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('минимум 50');
    });

    it('should accept content with at least 50 characters', () => {
      const content = 'A'.repeat(50);
      const result = MaterialFormValidator.validateContent(content, false, false);
      expect(result.valid).toBe(true);
    });
  });

  describe('Subject Validation', () => {
    it('should reject empty subject', () => {
      const result = MaterialFormValidator.validateSubject('');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('Выберите предмет');
    });

    it('should reject null subject', () => {
      const result = MaterialFormValidator.validateSubject(0);
      expect(result.valid).toBe(false);
    });

    it('should accept valid subject ID', () => {
      const result = MaterialFormValidator.validateSubject('1');
      expect(result.valid).toBe(true);
    });

    it('should accept valid subject as number', () => {
      const result = MaterialFormValidator.validateSubject(1);
      expect(result.valid).toBe(true);
    });
  });

  describe('Content Type Validation', () => {
    it('should reject empty type', () => {
      const result = MaterialFormValidator.validateContentType('');
      expect(result.valid).toBe(false);
    });

    it('should reject invalid type', () => {
      const result = MaterialFormValidator.validateContentType('invalid_type');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('Недопустимый');
    });

    it('should accept valid types', () => {
      const validTypes = ['lesson', 'presentation', 'video', 'document', 'test', 'homework'];
      validTypes.forEach((type) => {
        const result = MaterialFormValidator.validateContentType(type);
        expect(result.valid).toBe(true);
      });
    });
  });

  describe('Difficulty Level Validation', () => {
    it('should reject non-numeric difficulty', () => {
      const result = MaterialFormValidator.validateDifficultyLevel('abc');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('числом');
    });

    it('should reject difficulty below 1', () => {
      const result = MaterialFormValidator.validateDifficultyLevel(0);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('1 до 5');
    });

    it('should reject difficulty above 5', () => {
      const result = MaterialFormValidator.validateDifficultyLevel(6);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('1 до 5');
    });

    it('should accept difficulty levels 1-5', () => {
      for (let i = 1; i <= 5; i++) {
        const result = MaterialFormValidator.validateDifficultyLevel(i);
        expect(result.valid).toBe(true);
      }
    });

    it('should accept difficulty as string', () => {
      const result = MaterialFormValidator.validateDifficultyLevel('3');
      expect(result.valid).toBe(true);
    });
  });

  describe('Video URL Validation', () => {
    it('should accept empty video URL', () => {
      const result = MaterialFormValidator.validateVideoUrl('');
      expect(result.valid).toBe(true);
    });

    it('should accept YouTube URLs', () => {
      const urls = [
        'https://youtube.com/watch?v=dQw4w9WgXcQ',
        'https://youtu.be/dQw4w9WgXcQ',
      ];
      urls.forEach((url) => {
        const result = MaterialFormValidator.validateVideoUrl(url);
        expect(result.valid).toBe(true);
      });
    });

    it('should accept Vimeo URLs', () => {
      const urls = [
        'https://vimeo.com/123456',
        'https://player.vimeo.com/video/123456',
      ];
      urls.forEach((url) => {
        const result = MaterialFormValidator.validateVideoUrl(url);
        expect(result.valid).toBe(true);
      });
    });

    it('should accept relative paths', () => {
      const urls = ['/media/videos/lesson.mp4', './videos/intro.mp4'];
      urls.forEach((url) => {
        const result = MaterialFormValidator.validateVideoUrl(url);
        expect(result.valid).toBe(true);
      });
    });

    it('should accept HTTPS URLs for other video hosts', () => {
      const result = MaterialFormValidator.validateVideoUrl('https://example.com/video.mp4');
      expect(result.valid).toBe(true);
    });

    it('should reject invalid URL format', () => {
      const result = MaterialFormValidator.validateVideoUrl('not-a-url');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('URL');
    });

    it('should reject HTTP URLs for unsupported hosts', () => {
      const result = MaterialFormValidator.validateVideoUrl('http://example.com/video.mp4');
      expect(result.valid).toBe(false);
    });
  });

  describe('File Validation', () => {
    it('should accept null file', () => {
      const result = MaterialFormValidator.validateFile(null);
      expect(result.valid).toBe(true);
    });

    it('should reject file larger than 10MB', () => {
      const file = new File(['x'.repeat(11 * 1024 * 1024)], 'large.pdf', {
        type: 'application/pdf',
      });
      const result = MaterialFormValidator.validateFile(file);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('10MB');
    });

    it('should reject unsupported file type', () => {
      const file = new File(['content'], 'document.exe', { type: 'application/x-msdownload' });
      const result = MaterialFormValidator.validateFile(file);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('Неподдерживаемый');
    });

    it('should accept supported file types', () => {
      const supportedTypes = [
        { name: 'document.pdf', type: 'application/pdf' },
        { name: 'document.docx', type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
        { name: 'image.jpg', type: 'image/jpeg' },
        { name: 'image.png', type: 'image/png' },
      ];

      supportedTypes.forEach(({ name, type }) => {
        const file = new File(['content'], name, { type });
        const result = MaterialFormValidator.validateFile(file);
        expect(result.valid).toBe(true);
      });
    });

    it('should accept files at 10MB limit', () => {
      const file = new File(['x'.repeat(10 * 1024 * 1024)], 'document.pdf', {
        type: 'application/pdf',
      });
      const result = MaterialFormValidator.validateFile(file);
      expect(result.valid).toBe(true);
    });
  });

  describe('Full Form Validation', () => {
    it('should validate complete valid form', () => {
      const formData = {
        title: 'Valid Title',
        description: 'This is a valid description',
        content: 'A'.repeat(50),
        subject: '1',
        type: 'lesson',
        difficultyLevel: '3',
        videoUrl: '',
        file: null,
      };

      const result = MaterialFormValidator.validateForm(formData);
      expect(result.isValid).toBe(true);
      expect(result.errorCount).toBe(0);
      expect(Object.keys(result.errors)).toHaveLength(0);
    });

    it('should detect multiple validation errors', () => {
      const formData = {
        title: 'AB', // Too short
        description: 'Short', // Too short
        content: '', // Too short
        subject: '', // Missing
        type: 'invalid', // Invalid
        difficultyLevel: '10', // Out of range
        videoUrl: 'invalid-url', // Invalid URL
        file: null,
      };

      const result = MaterialFormValidator.validateForm(formData);
      expect(result.isValid).toBe(false);
      expect(result.errorCount).toBeGreaterThan(0);
      expect(Object.keys(result.errors).length).toBeGreaterThan(0);
    });

    it('should allow optional fields', () => {
      const formData = {
        title: 'Valid Title',
        description: '', // Optional
        content: 'A'.repeat(50),
        subject: '1',
        type: 'lesson',
        difficultyLevel: '1',
        videoUrl: '', // Optional
        file: null,
      };

      const result = MaterialFormValidator.validateForm(formData);
      expect(result.isValid).toBe(true);
    });

    it('should allow content with file', () => {
      const file = new File(['content'], 'document.pdf', { type: 'application/pdf' });
      const formData = {
        title: 'Valid Title',
        description: '',
        content: '', // Can be empty with file
        subject: '1',
        type: 'lesson',
        difficultyLevel: '1',
        videoUrl: '',
        file: file,
      };

      const result = MaterialFormValidator.validateForm(formData);
      expect(result.isValid).toBe(true);
    });

    it('should allow content with video', () => {
      const formData = {
        title: 'Valid Title',
        description: '',
        content: '', // Can be empty with video
        subject: '1',
        type: 'video',
        difficultyLevel: '2',
        videoUrl: 'https://youtube.com/watch?v=dQw4w9WgXcQ',
        file: null,
      };

      const result = MaterialFormValidator.validateForm(formData);
      expect(result.isValid).toBe(true);
    });
  });

  describe('Field Validation Context', () => {
    it('should validate content differently with file context', () => {
      // Without file: empty content is invalid
      const resultWithoutFile = MaterialFormValidator.validateContent('', false, false);
      expect(resultWithoutFile.valid).toBe(false);

      // With file: empty content is valid
      const resultWithFile = MaterialFormValidator.validateContent('', true, false);
      expect(resultWithFile.valid).toBe(true);
    });

    it('should validate content differently with video context', () => {
      // Without video: empty content is invalid
      const resultWithoutVideo = MaterialFormValidator.validateContent('', false, false);
      expect(resultWithoutVideo.valid).toBe(false);

      // With video: empty content is valid
      const resultWithVideo = MaterialFormValidator.validateContent('', false, true);
      expect(resultWithVideo.valid).toBe(true);
    });
  });

  describe('Text Sanitization', () => {
    it('should remove HTML tags from text', () => {
      const text = '<p>Hello</p><script>alert("xss")</script>';
      const sanitized = MaterialFormValidator.sanitizeText(text);
      expect(sanitized).not.toContain('<');
      expect(sanitized).not.toContain('>');
    });

    it('should handle empty strings', () => {
      const sanitized = MaterialFormValidator.sanitizeText('');
      expect(sanitized).toBe('');
    });
  });

  describe('Character Limits', () => {
    it('should display correct character limits in error messages', () => {
      const longTitle = 'A'.repeat(201);
      const result = MaterialFormValidator.validateTitle(longTitle);
      expect(result.error).toContain('200');
    });

    it('should have correct constant values', () => {
      expect(MaterialFormValidator.TITLE_MIN_LENGTH).toBe(3);
      expect(MaterialFormValidator.TITLE_MAX_LENGTH).toBe(200);
      expect(MaterialFormValidator.DESCRIPTION_MIN_LENGTH).toBe(10);
      expect(MaterialFormValidator.DESCRIPTION_MAX_LENGTH).toBe(5000);
      expect(MaterialFormValidator.CONTENT_MIN_LENGTH).toBe(50);
      expect(MaterialFormValidator.DIFFICULTY_MIN).toBe(1);
      expect(MaterialFormValidator.DIFFICULTY_MAX).toBe(5);
      expect(MaterialFormValidator.FILE_MAX_SIZE_MB).toBe(10);
    });
  });
});
