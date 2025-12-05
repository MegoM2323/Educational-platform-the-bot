import { useQuery, useQueryClient } from '@tanstack/react-query';
import { forumAPI, ForumChat } from '../integrations/api/forumAPI';

export const useForumChats = () => {
  return useQuery({
    queryKey: ['forum-chats'],
    queryFn: () => forumAPI.getForumChats(),
    staleTime: 60000, // 1 minute (reduced from 5 minutes for more frequent updates)
    retry: 2,
    refetchOnMount: true, // Explicitly enable refetch on component mount
    refetchOnWindowFocus: false,
  });
};

export const useForumChatsWithRefresh = () => {
  const queryClient = useQueryClient();

  const query = useForumChats();

  const refreshChats = () => {
    queryClient.invalidateQueries({ queryKey: ['forum-chats'] });
  };

  return { ...query, refreshChats };
};
