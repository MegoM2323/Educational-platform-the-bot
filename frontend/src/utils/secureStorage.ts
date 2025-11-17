// Утилиты для безопасного хранения токенов с шифрованием
import CryptoJS from 'crypto-js';

const STORAGE_KEY_PREFIX = 'bot_platform_';
const ENCRYPTION_KEY = 'bot_platform_secure_key_2024'; // В продакшене должен быть из переменных окружения

interface SecureStorageItem {
  data: string;
  timestamp: number;
  expires?: number;
}

class SecureStorage {
  private static instance: SecureStorage;
  private encryptionKey: string;

  private constructor() {
    // В продакшене ключ должен браться из переменных окружения
    this.encryptionKey = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_ENCRYPTION_KEY) || ENCRYPTION_KEY;
  }

  public static getInstance(): SecureStorage {
    if (!SecureStorage.instance) {
      SecureStorage.instance = new SecureStorage();
    }
    return SecureStorage.instance;
  }

  private encrypt(data: string): string {
    try {
      return CryptoJS.AES.encrypt(data, this.encryptionKey).toString();
    } catch (error) {
      console.error('Ошибка шифрования:', error);
      return data; // Возвращаем исходные данные в случае ошибки
    }
  }

  private decrypt(encryptedData: string): string | null {
    try {
      // Проверяем, что данные не пустые
      if (!encryptedData || encryptedData.trim() === '') {
        return null;
      }
      
      const bytes = CryptoJS.AES.decrypt(encryptedData, this.encryptionKey);
      const decrypted = bytes.toString(CryptoJS.enc.Utf8);
      
      // Проверяем, что расшифровка прошла успешно
      if (!decrypted || decrypted.trim() === '') {
        console.warn('Расшифровка вернула пустую строку - возможно, неверный ключ или поврежденные данные');
        return null;
      }
      
      return decrypted;
    } catch (error) {
      console.error('Ошибка расшифровки:', error);
      // Если данные повреждены, возвращаем null
      return null;
    }
  }

  private isExpired(item: SecureStorageItem): boolean {
    if (!item.expires) {
      return false;
    }
    return Date.now() > item.expires;
  }

  public setItem(key: string, value: string, ttl?: number): boolean {
    try {
      if (typeof window === 'undefined' || !window.localStorage) return false;
      
      const item: SecureStorageItem = {
        data: value,
        timestamp: Date.now(),
        expires: ttl ? Date.now() + ttl : undefined,
      };

      const encryptedItem = this.encrypt(JSON.stringify(item));
      localStorage.setItem(`${STORAGE_KEY_PREFIX}${key}`, encryptedItem);
      return true;
    } catch (error) {
      console.error('Ошибка сохранения в secure storage:', error);
      return false;
    }
  }

  public getItem(key: string): string | null {
    try {
      if (typeof window === 'undefined' || !window.localStorage) return null;

      const encryptedItem = localStorage.getItem(`${STORAGE_KEY_PREFIX}${key}`);
      if (!encryptedItem) {
        return null;
      }

      let item: SecureStorageItem;

      // Стратегия 1: Пытаемся распарсить как незашифрованный JSON
      try {
        const parsed = JSON.parse(encryptedItem);
        if (parsed && typeof parsed === 'object' && 'data' in parsed && 'timestamp' in parsed) {
          item = parsed as SecureStorageItem;

          // Проверяем истечение срока
          if (this.isExpired(item)) {
            this.removeItem(key);
            return null;
          }

          return item.data;
        }
      } catch (e) {
        // Не удалось распарсить как JSON, продолжаем
      }

      // Стратегия 2: Пытаемся расшифровать как зашифрованные данные
      const decryptedItem = this.decrypt(encryptedItem);
      if (!decryptedItem) {
        // Расшифровка не удалась - очищаем данные
        console.warn(`Failed to decrypt item with key: ${key}. Removing corrupted data.`);
        this.removeItem(key);
        return null;
      }

      // Парсим расшифрованный JSON
      try {
        item = JSON.parse(decryptedItem);
      } catch (e) {
        console.error(`Failed to parse decrypted item with key: ${key}`, e);
        this.removeItem(key);
        return null;
      }

      // Проверяем истечение срока
      if (this.isExpired(item)) {
        this.removeItem(key);
        return null;
      }

      return item.data;
    } catch (error) {
      console.error('Ошибка получения из secure storage:', error);
      return null;
    }
  }

  public removeItem(key: string): void {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.removeItem(`${STORAGE_KEY_PREFIX}${key}`);
      }
    } catch (error) {
      console.error('Ошибка удаления из secure storage:', error);
    }
  }

  public clear(): void {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const keys = Object.keys(localStorage);
        keys.forEach(key => {
          if (key.startsWith(STORAGE_KEY_PREFIX)) {
            localStorage.removeItem(key);
          }
        });
      }
    } catch (error) {
      console.error('Ошибка очистки secure storage:', error);
    }
  }

  public hasItem(key: string): boolean {
    return this.getItem(key) !== null;
  }

  // Специальные методы для токенов
  public setAuthToken(token: string, ttl?: number): boolean {
    return this.setItem('auth_token', token, ttl);
  }

  public getAuthToken(): string | null {
    return this.getItem('auth_token');
  }

  public setRefreshToken(token: string, ttl?: number): boolean {
    return this.setItem('refresh_token', token, ttl);
  }

  public getRefreshToken(): string | null {
    return this.getItem('refresh_token');
  }

  public setUserData(userData: any, ttl?: number): boolean {
    return this.setItem('user_data', JSON.stringify(userData), ttl);
  }

  public getUserData(): any | null {
    const data = this.getItem('user_data');
    if (!data) {
      return null;
    }
    try {
      return JSON.parse(data);
    } catch (error) {
      console.error('Ошибка парсинга user data:', error);
      return null;
    }
  }

  public clearAuthData(): void {
    this.removeItem('auth_token');
    this.removeItem('refresh_token');
    this.removeItem('user_data');
    this.removeItem('token_expiry');
  }
}

// Экспортируем singleton instance
export const secureStorage = SecureStorage.getInstance();

// Экспортируем класс для тестирования
export { SecureStorage };
