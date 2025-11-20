import { Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

/**
 * Создать тестовый PDF файл
 */
export async function createTestPDF(filename: string = 'test-document.pdf'): Promise<string> {
  const tempDir = os.tmpdir();
  const filePath = path.join(tempDir, filename);

  // Минимальный валидный PDF (header + trailer)
  const pdfContent = `%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF Document) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF`;

  fs.writeFileSync(filePath, pdfContent);
  return filePath;
}

/**
 * Создать тестовый текстовый файл
 */
export async function createTestTextFile(
  filename: string = 'test-document.txt',
  content: string = 'This is a test document for E2E testing.'
): Promise<string> {
  const tempDir = os.tmpdir();
  const filePath = path.join(tempDir, filename);

  fs.writeFileSync(filePath, content);
  return filePath;
}

/**
 * Создать тестовое изображение
 */
export async function createTestImage(filename: string = 'test-image.png'): Promise<string> {
  const tempDir = os.tmpdir();
  const filePath = path.join(tempDir, filename);

  // Минимальный валидный PNG (1x1 pixel, red)
  const pngContent = Buffer.from([
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d,
    0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xde, 0x00, 0x00, 0x00,
    0x0c, 0x49, 0x44, 0x41, 0x54, 0x08, 0xd7, 0x63, 0xf8, 0xcf, 0xc0, 0x00,
    0x00, 0x03, 0x01, 0x01, 0x00, 0x18, 0xdd, 0x8d, 0xb4, 0x00, 0x00, 0x00,
    0x00, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82,
  ]);

  fs.writeFileSync(filePath, pngContent);
  return filePath;
}

/**
 * Загрузить файл через input[type="file"]
 */
export async function uploadFile(
  page: Page,
  fileInputSelector: string,
  filePath: string
): Promise<void> {
  const fileInput = page.locator(fileInputSelector);
  await fileInput.setInputFiles(filePath);
}

/**
 * Ждать загрузки файла и проверить успех
 */
export async function waitForFileUploadSuccess(page: Page, timeout: number = 10000): Promise<void> {
  // Ищем индикаторы успешной загрузки
  await page.waitForSelector('text=/загружен|uploaded|успешно|success/i', {
    timeout,
    state: 'visible',
  });
}

/**
 * Скачать файл и проверить что он скачался
 */
export async function downloadFile(page: Page, downloadButtonSelector: string): Promise<string> {
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.click(downloadButtonSelector),
  ]);

  const filePath = await download.path();
  if (!filePath) {
    throw new Error('File download failed: no path returned');
  }

  return filePath;
}

/**
 * Очистить тестовые файлы
 */
export function cleanupTestFiles(filePaths: string[]): void {
  filePaths.forEach((filePath) => {
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
  });
}
