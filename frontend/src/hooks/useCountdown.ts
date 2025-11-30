import { useState, useEffect } from 'react';
import { differenceInSeconds, differenceInMinutes, differenceInHours, differenceInDays } from 'date-fns';

export interface CountdownResult {
  timeLeft: string;
  isUrgent: boolean;
  isStartingNow: boolean;
  totalSeconds: number;
}

export function useCountdown(targetDate: Date): CountdownResult {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const totalSeconds = differenceInSeconds(targetDate, now);

  if (totalSeconds <= 0) {
    return {
      timeLeft: 'Начинается сейчас!',
      isUrgent: false,
      isStartingNow: true,
      totalSeconds: 0,
    };
  }

  const days = differenceInDays(targetDate, now);
  const hours = differenceInHours(targetDate, now);
  const minutes = differenceInMinutes(targetDate, now);

  let timeLeft = '';
  if (days > 0) {
    timeLeft = `Через ${days} ${getDayWord(days)}`;
  } else if (hours > 0) {
    timeLeft = `Через ${hours} ${getHourWord(hours)}`;
  } else {
    timeLeft = `Через ${minutes} ${getMinuteWord(minutes)}`;
  }

  const isUrgent = hours < 1; // Less than 1 hour

  return {
    timeLeft,
    isUrgent,
    isStartingNow: false,
    totalSeconds,
  };
}

function getDayWord(count: number): string {
  if (count === 1) return 'день';
  if (count >= 2 && count <= 4) return 'дня';
  return 'дней';
}

function getHourWord(count: number): string {
  if (count === 1 || count === 21) return 'час';
  if (count >= 2 && count <= 4 || count >= 22 && count <= 24) return 'часа';
  return 'часов';
}

function getMinuteWord(count: number): string {
  if (count === 1 || count === 21 || count === 31 || count === 41 || count === 51) return 'минуту';
  if ((count >= 2 && count <= 4) || (count >= 22 && count <= 24) || (count >= 32 && count <= 34) || (count >= 42 && count <= 44) || (count >= 52 && count <= 54)) return 'минуты';
  return 'минут';
}
