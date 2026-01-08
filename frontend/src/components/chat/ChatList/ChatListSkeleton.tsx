import { Skeleton } from '@/components/ui/skeleton';

export const ChatListSkeleton = () => {
  return (
    <>
      <Skeleton className="h-20 rounded-lg" data-testid="chat-list-skeleton" />
      <Skeleton className="h-20 rounded-lg" data-testid="chat-list-skeleton" />
      <Skeleton className="h-20 rounded-lg" data-testid="chat-list-skeleton" />
    </>
  );
};
