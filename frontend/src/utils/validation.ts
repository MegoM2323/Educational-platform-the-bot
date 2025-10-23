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

export const validatePhone = (phone: string): boolean => {
  // Простая валидация для российских номеров
  const phoneRegex = /^(\+7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$/;
  return phoneRegex.test(phone.replace(/\s/g, ''));
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
