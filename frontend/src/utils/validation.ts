/**
 * Утилиты для валидации данных
 */

export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const validatePassword = (password: string): { isValid: boolean; message?: string } => {
  if (password.length < 6) {
    return { isValid: false, message: "Пароль должен содержать минимум 6 символов" };
  }
  
  if (password.length > 128) {
    return { isValid: false, message: "Пароль слишком длинный" };
  }
  
  return { isValid: true };
};

/**
 * Валидация телефонного номера
 * Синхронизировано с backend regex: ^\+?[1-9][\d]{4,15}$
 * Допускает: +79991234567, 79991234567, +7 (999) 123-45-67
 */
export const validatePhone = (phone: string): { isValid: boolean; message?: string } => {
  if (!phone) {
    return { isValid: false, message: "Телефон обязателен" };
  }

  // Удаляем все символы кроме цифр и +
  const cleanPhone = phone.replace(/[^\d+]/g, '');

  // Валидация в соответствии с Django (RegexValidator: ^\+?[1-9][\d]{4,15}$)
  const phoneRegex = /^\+?[1-9][\d]{4,15}$/;
  const isValid = phoneRegex.test(cleanPhone);

  if (!isValid) {
    return {
      isValid: false,
      message: "Номер телефона должен быть в формате: '+79991234567' или '+7 (999) 123-45-67'"
    };
  }

  return { isValid: true };
};

/**
 * Форматирует номер телефона в человеческий вид
 * Поддерживает форматы: +7 (999) 123-45-67 и международные номера
 */
export const formatPhoneNumber = (phone: string): string => {
  if (!phone) return '';

  // Удаляем все символы кроме цифр и +
  let cleaned = phone.replace(/[^\d+]/g, '');

  // Если нет +, добавляем его в начало (предполагаем Россию)
  if (!cleaned.startsWith('+') && cleaned.length >= 10) {
    if (cleaned.startsWith('7') && cleaned.length === 11) {
      cleaned = '+' + cleaned;
    } else if (cleaned.startsWith('8') && cleaned.length === 11) {
      cleaned = '+7' + cleaned.substring(1);
    } else if (!cleaned.startsWith('8') && !cleaned.startsWith('7')) {
      // Для других стран
      cleaned = '+' + cleaned;
    }
  }

  // Форматируем российские номера: +7 (999) 123-45-67
  if (cleaned.startsWith('+7') && cleaned.length === 12) {
    return `${cleaned.slice(0, 2)} (${cleaned.slice(2, 5)}) ${cleaned.slice(5, 8)}-${cleaned.slice(8, 10)}-${cleaned.slice(10, 12)}`;
  }

  // Для остальных возвращаем как есть
  return cleaned;
};

/**
 * Возвращает отформатированное значение для отправки на backend (без форматирования)
 */
export const getCleanPhone = (phone: string): string => {
  return phone.replace(/[^\d+]/g, '');
};

export const validateName = (name: string): { isValid: boolean; message?: string } => {
  if (name.length < 2) {
    return { isValid: false, message: "Имя должно содержать минимум 2 символа" };
  }
  
  if (name.length > 50) {
    return { isValid: false, message: "Имя слишком длинное" };
  }
  
  // Проверяем, что имя содержит только буквы, пробелы и дефисы
  const nameRegex = /^[а-яА-ЯёЁa-zA-Z\s\-]+$/;
  if (!nameRegex.test(name)) {
    return { isValid: false, message: "Имя может содержать только буквы, пробелы и дефисы" };
  }
  
  return { isValid: true };
};

export const getErrorMessage = (error: any): string => {
  if (!error) return "Неизвестная ошибка";
  
  const message = error.message || error.toString();
  
  // Обработка различных типов ошибок Supabase
  if (message.includes('Invalid login credentials')) {
    return "Неверный email или пароль";
  }
  
  if (message.includes('Email not confirmed')) {
    return "Пожалуйста, подтвердите email перед входом";
  }
  
  if (message.includes('User already registered')) {
    return "Пользователь с таким email уже зарегистрирован";
  }
  
  if (message.includes('Invalid email')) {
    return "Некорректный email адрес";
  }
  
  if (message.includes('Password should be at least')) {
    return "Пароль слишком короткий";
  }
  
  if (message.includes('Signup is disabled')) {
    return "Регистрация временно отключена";
  }
  
  if (message.includes('Email rate limit exceeded')) {
    return "Слишком много попыток. Попробуйте позже";
  }
  
  if (message.includes('Password rate limit exceeded')) {
    return "Слишком много попыток входа. Попробуйте позже";
  }
  
  // Возвращаем оригинальное сообщение, если не нашли специфичную обработку
  return message;
};
