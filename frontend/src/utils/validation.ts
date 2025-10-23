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

export const validatePhone = (phone: string): { isValid: boolean; message?: string } => {
  if (!phone) {
    return { isValid: false, message: "Телефон обязателен" };
  }
  
  // Валидация в соответствии с Django (RegexValidator: ^\+?1?\d{9,15}$)
  const phoneRegex = /^\+?1?\d{9,15}$/;
  const isValid = phoneRegex.test(phone);
  
  if (!isValid) {
    return { 
      isValid: false, 
      message: "Номер телефона должен быть в формате: '+79991234567'. До 15 цифр." 
    };
  }
  
  return { isValid: true };
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
