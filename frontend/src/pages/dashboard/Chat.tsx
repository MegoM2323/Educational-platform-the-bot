import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { logger } from "@/utils/logger";
import { useQueryClient, InfiniteData } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useChatRooms } from "@/hooks/useChatRooms";
import {
  useChatMessages,
  useSendChatMessage,
} from "@/hooks/useChatMessages";
import { Chat, ChatMessage, chatAPI } from "@/integrations/api/chatAPI";
import {
  chatWebSocketService,
  ChatMessage as WSChatMessage,
  TypingUser,
} from "@/services/chatWebSocketService";
import { useAuth } from "@/contexts/AuthContext";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { TutorSidebar } from "@/components/layout/TutorSidebar";
import { ParentSidebar } from "@/components/layout/ParentSidebar";
import { useToast } from "@/hooks/use-toast";
import { EditMessageDialog } from "@/components/chat/EditMessageDialog";
import { useChatMessageUpdate } from "@/hooks/useChatMessageUpdate";
import { useChatMessageDelete } from "@/hooks/useChatMessageDelete";
import { ChatList, ChatRoom, ContactsList } from "@/components/chat";

const getSidebarComponent = (role: string) => {
  switch (role) {
    case "student":
      return StudentSidebar;
    case "teacher":
      return TeacherSidebar;
    case "tutor":
      return TutorSidebar;
    case "parent":
      return ParentSidebar;
    default:
      return null;
  }
};

const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  if (error && typeof error === "object" && "message" in error) {
    return String(error.message);
  }
  return "Произошла ошибка";
};

function Chat() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [typingUsers, setTypingUsers] = useState<TypingUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isNewChatModalOpen, setIsNewChatModalOpen] = useState(false);
  const [isSwitchingChat, setIsSwitchingChat] = useState(false);
  const queryClient = useQueryClient();
  const typingTimeoutsRef = useRef<Map<number, NodeJS.Timeout>>(new Map());
  const switchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const previousChatIdRef = useRef<number | null>(null);
  const isMountedRef = useRef(true);

  const [editingMessage, setEditingMessage] = useState<{
    id: number;
    content: string;
  } | null>(null);
  const [deletingMessageId, setDeletingMessageId] = useState<number | null>(
    null,
  );
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const { chats = [], isLoadingChats, chatsError } = useChatRooms();

  const messagesQuery = useChatMessages(selectedChat?.id || null);
  const messages = useMemo(() => {
    if (!messagesQuery.data?.pages) return [];
    return messagesQuery.data.pages.flat();
  }, [messagesQuery.data?.pages]);
  const isLoadingMessages = messagesQuery.isLoading;
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = messagesQuery;

  const sendMessageMutation = useSendChatMessage();

  const editMessageMutation = useChatMessageUpdate({
    chatId: selectedChat?.id || 0,
    onSuccess: () => {
      setError(null);
      setEditingMessage(null);
    },
    onError: (error) => {
      setEditingMessage(null);
      toast({
        variant: "destructive",
        title: "Ошибка редактирования",
        description:
          getErrorMessage(error) || "Не удалось отредактировать сообщение",
      });
    },
  });

  const deleteMessageMutation = useChatMessageDelete({
    chatId: selectedChat?.id || 0,
    onSuccess: () => {
      setError(null);
      setDeletingMessageId(null);
      setIsDeleteConfirmOpen(false);
    },
    onError: (error) => {
      setDeletingMessageId(null);
      setIsDeleteConfirmOpen(false);
      toast({
        variant: "destructive",
        title: "Ошибка удаления",
        description: getErrorMessage(error) || "Не удалось удалить сообщение",
      });
    },
  });

  const handleWebSocketMessage = useCallback(
    (wsMessage: WSChatMessage) => {
      try {
        logger.debug(
          "[Chat] WebSocket message received in component handler:",
          {
            messageId: wsMessage.id,
            content: wsMessage.content.substring(0, 50),
            senderId: wsMessage.sender.id,
            selectedChatId: selectedChat?.id,
          },
        );

        if (!selectedChat) {
          logger.warn("[Chat] Received message but no chat selected");
          return;
        }

        const chatMessage: ChatMessage = {
          id: wsMessage.id,
          content: wsMessage.content,
          sender: {
            id: wsMessage.sender.id,
            full_name:
              `${wsMessage.sender.first_name} ${wsMessage.sender.last_name}`.trim() ||
              wsMessage.sender.username,
            role: wsMessage.sender.role,
          },
          created_at: wsMessage.created_at,
          updated_at: wsMessage.updated_at,
          is_read: wsMessage.is_read,
          is_edited: wsMessage.is_edited || false,
          message_type: wsMessage.message_type,
        };

        logger.debug(
          "[Chat] Updating TanStack Query cache for chat:",
          selectedChat.id,
        );
        queryClient.setQueriesData<InfiniteData<ChatMessage[]>>(
          { queryKey: ["chat-messages", selectedChat.id], exact: false },
          (oldData) => {
            if (!oldData || !oldData.pages) {
              logger.debug(
                "[Chat] No existing data, creating new InfiniteData with message",
              );
              return {
                pages: [[chatMessage]],
                pageParams: [0],
              };
            }

            const exists = oldData.pages.some((page) =>
              page.some((msg) => msg.id === chatMessage.id),
            );

            if (exists) {
              logger.debug("[Chat] Message already exists in cache, skipping");
              return oldData;
            }

            logger.debug(
              "[Chat] Adding new message to last page of InfiniteData",
            );
            const newPages = [...oldData.pages];
            const lastPageIndex = newPages.length - 1;
            newPages[lastPageIndex] = [...newPages[lastPageIndex], chatMessage];

            return {
              ...oldData,
              pages: newPages,
            };
          },
        );

        queryClient.invalidateQueries({ queryKey: ["chat", "chats"] });
        setError(null);
      } catch (err) {
        logger.error("[Chat] WebSocket handler error:", err);
        toast({
          variant: "destructive",
          title: "Ошибка обработки сообщения",
          description: "Не удалось обработать полученное сообщение",
        });
        setError("Ошибка обработки сообщения");
      }
    },
    [selectedChat, queryClient],
  );

  const handleTyping = useCallback((user: TypingUser, roomId?: number) => {
    setTypingUsers((prev) => {
      const filtered = prev.filter((u) => u.id !== user.id);
      return [...filtered, user];
    });

    const timeoutKey = roomId?.toString() || "general";

    const existingTimeout = typingTimeoutsRef.current.get(user.id);
    if (existingTimeout) {
      clearTimeout(existingTimeout);
    }

    const timeoutId = setTimeout(() => {
      setTypingUsers((prev) => prev.filter((u) => u.id !== user.id));
      typingTimeoutsRef.current.delete(user.id);
    }, 3000);

    typingTimeoutsRef.current.set(user.id, timeoutId);
  }, []);

  const handleTypingStop = useCallback((user: TypingUser) => {
    setTypingUsers((prev) => prev.filter((u) => u.id !== user.id));

    const existingTimeout = typingTimeoutsRef.current.get(user.id);
    if (existingTimeout) {
      clearTimeout(existingTimeout);
      typingTimeoutsRef.current.delete(user.id);
    }
  }, []);

  const handleError = useCallback((errorMessage: string) => {
    logger.error("WebSocket error:", errorMessage);
    setError(errorMessage);
  }, []);

  useEffect(() => {
    if (!selectedChat || !user) return;

    const chatId = selectedChat.id;
    let isEffectActive = true;

    logger.debug(
      "[Chat] Chat selected, setting up WebSocket for chat:",
      chatId,
    );

    const handlers = {
      onMessage: handleWebSocketMessage,
      onTyping: handleTyping,
      onTypingStop: handleTypingStop,
      onError: handleError,
    };

    // Disconnect from previous chat if it exists
    if (previousChatIdRef.current && previousChatIdRef.current !== chatId) {
      logger.debug(
        "[Chat] Disconnecting from previous chat:",
        previousChatIdRef.current,
      );
      chatWebSocketService.disconnectFromRoom(previousChatIdRef.current);
    }

    (async () => {
      try {
        if (!isEffectActive) {
          logger.debug(
            "[Chat] Effect unmounted, skipping WebSocket connection",
          );
          return;
        }

        logger.debug("[Chat] Connecting to chat room:", chatId);
        const connectionSuccess = await chatWebSocketService.connectToRoom(
          chatId,
          handlers,
        );

        if (!connectionSuccess) {
          logger.error("[Chat] Failed to connect to chat room:", chatId);
          if (isEffectActive) {
            setError("Не удалось подключиться к чату. Проверьте авторизацию.");
            setIsSwitchingChat(false);
          }
        } else {
          logger.debug("[Chat] Successfully connected to chat room:", chatId);
          if (isEffectActive) {
            setIsSwitchingChat(false);
          }
        }
      } catch (error) {
        logger.error("[Chat] WebSocket connection failed:", error);
        if (isEffectActive) {
          setIsSwitchingChat(false);
          setError("Не удалось подключиться к чату");
        }
      }
    })();

    // Update the previous chat ID ref
    previousChatIdRef.current = chatId;

    const initiallyConnected = chatWebSocketService.isConnected();
    logger.debug("[Chat] Initial connection state:", initiallyConnected);
    if (isEffectActive) {
      setIsConnected(initiallyConnected);
      if (initiallyConnected) {
        setError(null);
      }
    }

    const connectionCallback = (connected: boolean) => {
      logger.debug("[Chat] Connection state changed to:", connected);
      if (isEffectActive) {
        setIsConnected(connected);
        if (!connected) {
          setError("Соединение потеряно. Попытка переподключения...");
        } else {
          setError(null);
        }
      }
    };

    chatWebSocketService.onConnectionChange(connectionCallback);

    return () => {
      isEffectActive = false;

      logger.debug("[Chat] Cleaning up WebSocket for chat:", chatId);
      if (previousChatIdRef.current) {
        chatWebSocketService.disconnectFromRoom(previousChatIdRef.current);
      }
      setTypingUsers([]);

      typingTimeoutsRef.current.forEach((timeoutId) => clearTimeout(timeoutId));
      typingTimeoutsRef.current.clear();
    };
  }, [
    selectedChat,
    user,
    handleWebSocketMessage,
    handleTyping,
    handleTypingStop,
    handleError,
  ]);

  const handleSelectChat = async (chat: Chat) => {
    if (switchTimeoutRef.current) {
      clearTimeout(switchTimeoutRef.current);
    }

    switchTimeoutRef.current = setTimeout(async () => {
      setIsSwitchingChat(true);
      setError(null);
      setTypingUsers([]);

      const previousChatId = selectedChat?.id;
      if (previousChatId && previousChatId !== chat.id) {
        logger.debug(
          "[Chat] Clearing message cache for previous chat:",
          previousChatId,
        );
        queryClient.removeQueries({
          queryKey: ["chat-messages", previousChatId],
        });
      }

      setSelectedChat(chat);
      setSearchQuery("");

      if (previousChatId && previousChatId !== chat.id) {
        await queryClient.cancelQueries({
          queryKey: ["chat-messages", previousChatId],
        });
      }

      if (chat.unread_count > 0) {
        try {
          await chatAPI.markAsRead(chat.id);
          queryClient.setQueryData<Chat[]>(["chat", "chats"], (oldChats) => {
            if (!oldChats) return oldChats;
            return oldChats.map((c) =>
              c.id === chat.id ? { ...c, unread_count: 0 } : c,
            );
          });
        } catch (error) {
          logger.error("Failed to mark chat as read:", error);
        }
      }

      setTimeout(() => {
        if (isMountedRef.current) {
          setIsSwitchingChat(false);
        }
      }, 500);
    }, 200);
  };

  const handleSendMessage = (content: string, file?: File) => {
    if (!selectedChat) {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Чат не выбран",
      });
      return;
    }

    setError(null);

    sendMessageMutation.mutate({
      chatId: selectedChat.id,
      data: { content },
      file,
    });
  };

  const handleRetryConnection = () => {
    setError(null);
    if (selectedChat) {
      const chat = selectedChat;
      setSelectedChat(null);
      setTimeout(() => {
        setSelectedChat(chat);
      }, 100);
    }
  };

  const handleChatInitiated = useCallback(
    (chatId: number) => {
      logger.debug("[Chat] Chat initiated, selecting chat:", chatId);

      queryClient
        .invalidateQueries({ queryKey: ["chat", "chats"] })
        .then(() => {
          if (!isMountedRef.current) {
            logger.debug(
              "[Chat] Component unmounted, skipping chat selection",
            );
            return;
          }

          const updatedChats = queryClient.getQueryData<Chat[]>([
            "chat",
            "chats",
          ]);
          const newChat = updatedChats?.find((chat) => chat.id === chatId);

          if (newChat) {
            setSelectedChat(newChat);
          }
        });
    },
    [queryClient],
  );

  const handleEditMessage = (messageId: number, content: string) => {
    setEditingMessage({ id: messageId, content });
  };

  const handleSaveEdit = (newContent: string) => {
    if (editingMessage) {
      editMessageMutation.mutate({
        messageId: editingMessage.id,
        data: { content: newContent },
      });
    }
  };

  const handleDeleteMessage = (messageId: number) => {
    setDeletingMessageId(messageId);
    setIsDeleteConfirmOpen(true);
  };

  const handleConfirmDelete = () => {
    if (deletingMessageId) {
      deleteMessageMutation.mutate(deletingMessageId);
    }
  };

  const handleTypingIndicator = useCallback(() => {
    if (isConnected && selectedChat) {
      chatWebSocketService.sendTyping(selectedChat.id);
      chatWebSocketService.startTypingTimer(selectedChat.id);
    }
  }, [isConnected, selectedChat]);

  const SidebarComponent = getSidebarComponent(user?.role || "");

  if (!SidebarComponent) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-muted-foreground">Неизвестная роль пользователя</p>
      </div>
    );
  }

  return (
    <SidebarProvider>
      <div className="flex h-screen w-full overflow-hidden">
        <SidebarComponent />
        <SidebarInset className="flex flex-col h-full overflow-hidden">
          <header className="flex-shrink-0 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <h1 className="text-2xl font-bold ml-4">Форум</h1>
            <div className="flex-1" />
            {user?.role !== "admin" && (
              <Button
                type="button"
                variant="default"
                size="sm"
                onClick={() => setIsNewChatModalOpen(true)}
                className="gradient-primary"
              >
                <Plus className="w-4 h-4 mr-2" />
                Новый чат
              </Button>
            )}
          </header>
          <main className="flex-1 overflow-hidden flex flex-col p-6 min-h-0">
            <div className="flex-shrink-0 mb-4">
              <p className="text-muted-foreground">
                Общайтесь с преподавателями и тьюторами
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 flex-1 overflow-hidden min-h-0">
              <ChatList
                chats={chats}
                selectedChat={selectedChat}
                onSelectChat={handleSelectChat}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                isLoading={isLoadingChats}
                currentUserId={user?.id || 0}
              />

              <ChatRoom
                chat={selectedChat}
                messages={messages}
                isLoadingMessages={isLoadingMessages}
                isSending={sendMessageMutation.isPending}
                onSendMessage={handleSendMessage}
                isConnected={isConnected}
                error={error}
                onRetryConnection={handleRetryConnection}
                onEditMessage={handleEditMessage}
                onDeleteMessage={handleDeleteMessage}
                isEditingOrDeleting={
                  editMessageMutation.isPending ||
                  deleteMessageMutation.isPending
                }
                currentUserId={user?.id || 0}
                currentUserRole={user?.role || ""}
                isSwitchingChat={isSwitchingChat}
                fetchNextPage={fetchNextPage}
                hasNextPage={hasNextPage}
                isFetchingNextPage={isFetchingNextPage}
                onTyping={handleTypingIndicator}
              />
            </div>
          </main>
        </SidebarInset>
      </div>

      <ContactsList
        isOpen={isNewChatModalOpen}
        onClose={() => setIsNewChatModalOpen(false)}
        onSelectContact={handleChatInitiated}
      />

      <EditMessageDialog
        isOpen={editingMessage !== null}
        onClose={() => setEditingMessage(null)}
        messageContent={editingMessage?.content || ""}
        onSave={handleSaveEdit}
        isLoading={editMessageMutation.isPending}
      />

      <AlertDialog
        open={isDeleteConfirmOpen}
        onOpenChange={(open) => {
          setIsDeleteConfirmOpen(open);
          if (!open) {
            setDeletingMessageId(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить сообщение?</AlertDialogTitle>
            <AlertDialogDescription>
              Это действие нельзя отменить. Сообщение будет удалено из чата.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={() => {
                setIsDeleteConfirmOpen(false);
                setDeletingMessageId(null);
              }}
            >
              Отмена
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMessageMutation.isPending ? "Удаление..." : "Удалить"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </SidebarProvider>
  );
}

export default Chat;
