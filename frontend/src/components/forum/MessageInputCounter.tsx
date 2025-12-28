import { cn } from '@/lib/utils';

interface MessageInputCounterProps {
  currentLength: number;
  maxLength: number;
}

export const MessageInputCounter = ({ currentLength, maxLength }: MessageInputCounterProps) => {
  if (currentLength === 0) return null;

  return (
    <div className="mb-2 flex justify-end">
      <div
        className={cn(
          'text-xs',
          currentLength > maxLength
            ? 'text-destructive font-medium'
            : currentLength > maxLength * 0.9
            ? 'text-yellow-600'
            : 'text-muted-foreground'
        )}
      >
        {currentLength}/{maxLength}
      </div>
    </div>
  );
};
