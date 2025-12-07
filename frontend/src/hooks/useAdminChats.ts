import { useQuery } from '@tanstack/react-query';
import { adminAPI } from '@/integrations/api/adminAPI';
import { useState } from 'react';

/**
 * Custom hook for admin chat management
 * Provides access to all chat rooms with caching and room selection
 */
export const useAdminChats = () => {
  const [selectedRoomId, setSelectedRoomId] = useState<number | null>(null);

  // Fetch all chat rooms
  const {
    data: roomsData,
    isLoading: roomsLoading,
    error: roomsError,
    refetch: refetchRooms,
  } = useQuery({
    queryKey: ['admin', 'chats', 'rooms'],
    queryFn: () => adminAPI.getChatRooms(),
    staleTime: 60000, // 1 minute
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  });

  // Fetch chat statistics
  const {
    data: statsData,
    isLoading: statsLoading,
    error: statsError,
  } = useQuery({
    queryKey: ['admin', 'chats', 'stats'],
    queryFn: () => adminAPI.getChatStats(),
    staleTime: 300000, // 5 minutes
    refetchOnWindowFocus: false,
  });

  // Fetch detailed room info for selected room
  const {
    data: roomDetailData,
    isLoading: roomDetailLoading,
    error: roomDetailError,
  } = useQuery({
    queryKey: ['admin', 'chats', 'room-detail', selectedRoomId],
    queryFn: () => {
      if (!selectedRoomId) {
        throw new Error('No room selected');
      }
      return adminAPI.getChatRoomDetail(selectedRoomId);
    },
    enabled: selectedRoomId !== null,
    staleTime: 60000, // 1 minute
    refetchOnWindowFocus: false,
  });

  return {
    // Rooms
    rooms: roomsData?.data?.rooms || [],
    roomsCount: roomsData?.data?.count || 0,
    roomsLoading,
    roomsError: roomsError?.message,

    // Stats
    stats: statsData?.data || null,
    statsLoading,
    statsError: statsError?.message,

    // Room detail
    roomDetail: roomDetailData?.data?.room || null,
    roomDetailLoading,
    roomDetailError: roomDetailError?.message,

    // Room selection
    selectedRoomId,
    setSelectedRoomId,

    // Refetch functions
    refetchRooms,

    // Combined loading state
    isLoading: roomsLoading || statsLoading,
  };
};

/**
 * Hook for fetching chat messages with pagination
 * Use this for displaying messages for a specific room
 */
export const useAdminChatMessages = (
  roomId: number | null,
  options?: {
    limit?: number;
    offset?: number;
  }
) => {
  const {
    data: messagesData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['admin', 'chats', 'messages', roomId, options],
    queryFn: () => {
      if (!roomId) {
        throw new Error('Room ID is required');
      }
      return adminAPI.getChatMessages(roomId, options);
    },
    enabled: roomId !== null,
    staleTime: 30000, // 30 seconds
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  });

  return {
    messages: messagesData?.data?.messages || [],
    messagesCount: messagesData?.data?.count || 0,
    limit: messagesData?.data?.limit || options?.limit || 100,
    offset: messagesData?.data?.offset || options?.offset || 0,
    isLoading,
    error: error?.message,
    refetch,
  };
};
