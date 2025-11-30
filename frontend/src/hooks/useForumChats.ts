import { useQuery, useQueryClient } from '@tanstack/react-query';
import { forumAPI, ForumChat } from '../integrations/api/forumAPI';

export const useForumChats = () => {
  return useQuery({
    queryKey: ['forum-chats'],
    queryFn: () => forumAPI.getForumChats(),
    staleTime: 300000, // 5 minutes
    retry: 2,
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
