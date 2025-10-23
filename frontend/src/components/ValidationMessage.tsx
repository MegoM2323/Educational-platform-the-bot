import { useState, useEffect } from 'react';
import { validateEmail, validatePassword, validateName, validatePhone } from '@/utils/validation';

interface ValidationMessageProps {
  type: 'email' | 'password' | 'name' | 'phone';
  value: string;
  show?: boolean;
}

export const ValidationMessage = ({ type, value, show = true }: ValidationMessageProps) => {
  const [message, setMessage] = useState<string>('');
  const [isValid, setIsValid] = useState<boolean>(true);

  useEffect(() => {
    if (!value || !show) {
      setMessage('');
      setIsValid(true);
      return;
    }

    let validation: { isValid: boolean; message?: string } = { isValid: true };

    switch (type) {
      case 'email':
        const emailValid = validateEmail(value);
        validation = { isValid: emailValid, message: emailValid ? '' : 'Некорректный email адрес' };
        break;
      case 'password':
        validation = validatePassword(value);
        break;
      case 'name':
        validation = validateName(value);
        break;
      case 'phone':
        validation = validatePhone(value);
        break;
    }

    setIsValid(validation.isValid);
    setMessage(validation.isValid ? '' : validation.message || '');
  }, [type, value, show]);

  if (!message) return null;

  return (
    <div className={`text-sm mt-1 ${isValid ? 'text-green-600' : 'text-red-600'}`}>
      {message}
    </div>
  );
};
