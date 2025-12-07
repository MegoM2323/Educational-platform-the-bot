/**
 * useWindowSize Hook
 * Отслеживает размер окна для responsive компонентов
 */

import { useState, useEffect } from 'react';

export interface WindowSize {
  width: number;
  height: number;
}

export const useWindowSize = (): WindowSize => {
  const [windowSize, setWindowSize] = useState<WindowSize>({
    width: typeof window !== 'undefined' ? window.innerWidth : 1200,
    height: typeof window !== 'undefined' ? window.innerHeight : 800,
  });

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const handleResize = () => {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    // Добавить listener
    window.addEventListener('resize', handleResize);

    // Вызвать сразу для получения актуального размера
    handleResize();

    // Cleanup
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return windowSize;
};
