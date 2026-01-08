import React, { useState, useEffect } from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { StudentSidebar } from '@/components/layout/StudentSidebar';
import { ChatList, ChatWindow, ContactSelector, MessageInput } from '@/components/chat';
import { useAuth } from '@/contexts/AuthContext';
import { Navigate } from 'react-router-dom';
import {
  useChatList,
  useChatMessages,
  useSendChatMessage,
  useWebSocketChat,
  useUnreadCount,
} from '@/hooks/useChat';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MessageSquare, Plus } from 'lucide-react';
import { logger } from '@/utils/logger';
import { ForumChat } from '@/integrations/api/forumAPI';

export default function StudentChatPage(): JSX.Element {
  const { user } = useAuth();
  const [selectedChat, setSelectedChat] = useState<ForumChat | null>(null);
  const [showNewChatModal, setShowNewChatModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [messageText, setMessageText] = useState('');

  const { data: chatListData, isLoading: chatsLoading } = useChatList();
  const { data: messagesData, isLoading: messagesLoading } = useChatMessages(selectedChat?.id || 0);
  const sendMutation = useSendChatMessage();
  const unreadCount = useUnreadCount();

  const { isConnected: wsConnected, error: wsError } = useWebSocketChat(
    selectedChat?.id || 0,
    !!selectedChat?.id
  );

  if (user?.role !== 'student') {
    return <Navigate to="/dashboard" replace />;
  }

  const chats = chatListData?.results || [];

  const filteredChats = searchQuery.trim()
    ? chats.filter((chat) => {
        const displayName =
          chat.name ||
          chat.participants
            .filter((p) => p.id !== user.id)
            .map((p) => p.full_name)
            .join(', ');
        return displayName.toLowerCase().includes(searchQuery.toLowerCase());
      })
    : chats;

  const handleSelectChat = (chat: ForumChat) => {
    setSelectedChat(chat);
    setSearchQuery('');
  };

  const handleSendMessage = async (content: string, attachments?: File[]) => {
    if (!selectedChat || !content.trim()) return;

    try {
      await sendMutation.mutateAsync({
        chatId: selectedChat.id,
        data: {
          content,
          attachments: attachments || [],
        },
      });
    } catch (error) {
      logger.error('Failed to send message:', error);
    }
  };

  const handleCreateNewChat = (contactId: number) => {
    const existingChat = chats.find(
      (chat) => chat.participants.some((p) => p.id === contactId) && chat.participants.length === 2
    );

    if (existingChat) {
      setSelectedChat(existingChat);
    }

    setShowNewChatModal(false);
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background">
        <StudentSidebar />
        <SidebarInset className="flex-1">
          {/* Header */}
          <header className="sticky top-0 z-10 flex h-16 items-center border-b bg-background px-6">
            <SidebarTrigger />
            <h1 className="ml-4 text-xl font-semibold flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              Сообщения
            </h1>
            {unreadCount > 0 && (
              <span className="ml-2 inline-flex items-center justify-center rounded-full bg-destructive px-2.5 py-0.5 text-xs font-medium text-destructive-foreground">
                {unreadCount}
              </span>
            )}
          </header>

          {/* Main Content */}
          <main className="flex-1 overflow-hidden">
            <div className="flex h-[calc(100vh-4rem)] gap-4 p-4">
              {/* Chat List - Always visible on mobile, left side on desktop */}
              <div className="w-full md:w-1/3 flex flex-col">
                <Card className="flex flex-col flex-1">
                  {/* Header with New Chat Button */}
                  <div className="flex items-center justify-between border-b p-4">
                    <h2 className="font-semibold">Чаты</h2>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setShowNewChatModal(true)}
                      className="gap-1"
                    >
                      <Plus className="w-4 h-4" />
                      <span className="hidden sm:inline">Новый</span>
                    </Button>
                  </div>

                  {/* Chat List */}
                  <ChatList
                    chats={filteredChats}
                    selectedChat={selectedChat}
                    onSelectChat={handleSelectChat}
                    searchQuery={searchQuery}
                    onSearchChange={setSearchQuery}
                    isLoading={chatsLoading}
                    currentUserId={user?.id || 0}
                  />
                </Card>
              </div>

              {/* Chat Window - Hidden on mobile, visible on desktop */}
              <div className="hidden md:flex w-2/3 flex-col">
                {selectedChat ? (
                  <ChatWindow
                    chatId={selectedChat.id}
                    messages={messagesData?.results || []}
                    isLoading={messagesLoading}
                    isConnected={wsConnected}
                    renderMessageInput={() => (
                      <MessageInput
                        value={messageText}
                        onChange={setMessageText}
                        onSend={async () => {
                          if (!messageText.trim()) return;
                          await handleSendMessage(messageText);
                          setMessageText('');
                        }}
                        isLoading={sendMutation.isPending}
                      />
                    )}
                  />
                ) : (
                  <Card className="flex flex-1 items-center justify-center">
                    <div className="text-center">
                      <MessageSquare className="mx-auto mb-4 h-12 w-12 text-muted-foreground opacity-50" />
                      <p className="text-lg font-medium">Выберите чат для начала переписки</p>
                      <p className="mt-2 text-sm text-muted-foreground">
                        Нажмите на чат в списке слева или создайте новый
                      </p>
                      <Button onClick={() => setShowNewChatModal(true)} className="mt-4 gap-2">
                        <Plus className="w-4 h-4" />
                        Создать новый чат
                      </Button>
                    </div>
                  </Card>
                )}
              </div>

              {/* Mobile Chat Window - Visible when chat selected on mobile */}
              {selectedChat && (
                <div className="absolute inset-0 z-50 flex flex-col md:hidden bg-background">
                  <header className="flex h-16 items-center border-b bg-background px-4">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedChat(null)}
                      className="mr-2"
                    >
                      ←
                    </Button>
                    <h2 className="font-semibold">
                      {selectedChat.name ||
                        selectedChat.participants
                          .filter((p) => p.id !== user?.id)
                          .map((p) => p.full_name)
                          .join(', ')}
                    </h2>
                  </header>
                  <ChatWindow
                    chatId={selectedChat.id}
                    messages={messagesData?.results || []}
                    isLoading={messagesLoading}
                    isConnected={wsConnected}
                    renderMessageInput={() => (
                      <MessageInput
                        value={messageText}
                        onChange={setMessageText}
                        onSend={async () => {
                          if (!messageText.trim()) return;
                          await handleSendMessage(messageText);
                          setMessageText('');
                        }}
                        isLoading={sendMutation.isPending}
                      />
                    )}
                  />
                </div>
              )}
            </div>
          </main>

          {/* New Chat Modal */}
          {showNewChatModal && (
            <ContactSelector
              isOpen={showNewChatModal}
              onClose={() => setShowNewChatModal(false)}
              onChatInitiated={(chatId) => {
                setSelectedChat(chatListData?.results.find(c => c.id === chatId) || null);
                setShowNewChatModal(false);
              }}
            />
          )}
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}

export { StudentChatPage };
