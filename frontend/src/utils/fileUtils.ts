/**
 * File utilities for handling file types, sizes, and validation
 */

import {
  FileText,
  FileImage,
  FileArchive,
  File as FileIcon,
  Presentation,
  type LucideIcon
} from "lucide-react";

/**
 * Get the appropriate icon for a file based on its filename
 * @param filename - The name of the file
 * @returns The Lucide icon component for the file type
 */
export function getFileIcon(filename: string): LucideIcon {
  if (!filename) return FileIcon;

  const extension = filename.split('.').pop()?.toLowerCase();

  switch (extension) {
    case 'pdf':
      return FileText;
    case 'doc':
    case 'docx':
      return FileText;
    case 'ppt':
    case 'pptx':
      return Presentation;
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'gif':
    case 'webp':
    case 'svg':
      return FileImage;
    case 'zip':
    case 'rar':
    case '7z':
    case 'tar':
    case 'gz':
      return FileArchive;
    case 'txt':
    case 'md':
    case 'csv':
      return FileText;
    default:
      return FileIcon;
  }
}

/**
 * Get the color for a file icon based on its type
 * @param filename - The name of the file
 * @returns Tailwind CSS color class for the icon
 */
export function getFileIconColor(filename: string): string {
  if (!filename) return 'text-gray-500';

  const extension = filename.split('.').pop()?.toLowerCase();

  switch (extension) {
    case 'pdf':
      return 'text-red-500';
    case 'doc':
    case 'docx':
      return 'text-blue-500';
    case 'ppt':
    case 'pptx':
      return 'text-orange-500';
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'gif':
    case 'webp':
    case 'svg':
      return 'text-green-500';
    case 'zip':
    case 'rar':
    case '7z':
    case 'tar':
    case 'gz':
      return 'text-purple-500';
    default:
      return 'text-gray-500';
  }
}

/**
 * Format file size from bytes to human-readable string
 * @param bytes - The size in bytes
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted string like "2.5 MB"
 */
export function formatFileSize(bytes: number, decimals: number = 2): string {
  if (bytes === 0) return '0 Bytes';
  if (bytes < 0) return 'Invalid size';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  if (i >= sizes.length) {
    return `${(bytes / Math.pow(k, sizes.length - 1)).toFixed(dm)} ${sizes[sizes.length - 1]}`;
  }

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

/**
 * Validate file size against a maximum size
 * @param file - The File object to validate
 * @param maxMB - Maximum file size in megabytes
 * @returns Object with isValid boolean and error message if invalid
 */
export function validateFileSize(
  file: File,
  maxMB: number
): { isValid: boolean; error?: string } {
  const maxBytes = maxMB * 1024 * 1024;

  if (file.size > maxBytes) {
    return {
      isValid: false,
      error: `Файл "${file.name}" слишком большой. Максимальный размер: ${maxMB} MB, размер файла: ${formatFileSize(file.size)}`
    };
  }

  return { isValid: true };
}

/**
 * Validate multiple files against a maximum size
 * @param files - Array of File objects to validate
 * @param maxMB - Maximum file size in megabytes per file
 * @returns Object with isValid boolean and array of error messages
 */
export function validateFileSizes(
  files: File[],
  maxMB: number
): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];

  for (const file of files) {
    const validation = validateFileSize(file, maxMB);
    if (!validation.isValid && validation.error) {
      errors.push(validation.error);
    }
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Validate file type against allowed extensions
 * @param file - The File object to validate
 * @param allowedExtensions - Array of allowed extensions (e.g., ['pdf', 'doc', 'docx'])
 * @returns Object with isValid boolean and error message if invalid
 */
export function validateFileType(
  file: File,
  allowedExtensions: string[]
): { isValid: boolean; error?: string } {
  const extension = file.name.split('.').pop()?.toLowerCase();

  if (!extension || !allowedExtensions.includes(extension)) {
    return {
      isValid: false,
      error: `Недопустимый формат файла "${file.name}". Разрешенные форматы: ${allowedExtensions.join(', ')}`
    };
  }

  return { isValid: true };
}

/**
 * Get file extension from filename
 * @param filename - The name of the file
 * @returns The file extension in lowercase, or empty string if none
 */
export function getFileExtension(filename: string): string {
  return filename.split('.').pop()?.toLowerCase() || '';
}

/**
 * Check if a file is an image
 * @param filename - The name of the file
 * @returns True if the file is an image
 */
export function isImageFile(filename: string): boolean {
  const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico'];
  const extension = getFileExtension(filename);
  return imageExtensions.includes(extension);
}

/**
 * Check if a file is a document
 * @param filename - The name of the file
 * @returns True if the file is a document
 */
export function isDocumentFile(filename: string): boolean {
  const docExtensions = ['pdf', 'doc', 'docx', 'txt', 'md', 'csv', 'xls', 'xlsx'];
  const extension = getFileExtension(filename);
  return docExtensions.includes(extension);
}

/**
 * Check if a file is an archive
 * @param filename - The name of the file
 * @returns True if the file is an archive
 */
export function isArchiveFile(filename: string): boolean {
  const archiveExtensions = ['zip', 'rar', '7z', 'tar', 'gz'];
  const extension = getFileExtension(filename);
  return archiveExtensions.includes(extension);
}
