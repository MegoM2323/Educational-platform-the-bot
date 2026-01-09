import React, { useState } from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { TeacherSidebar } from '@/components/layout/TeacherSidebar';
import { useAuth } from '@/contexts/AuthContext';
import { Navigate } from 'react-router-dom';
import { useGeneralChat, useGeneralChatMessages, useSendGeneralMessage } from '@/hooks/useGeneralChatHooks';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MessageSquare } from 'lucide-react';
import { logger } from '@/utils/logger';

export default function TeacherChatPage(): JSX.Element {
  const { user } = useAuth();
  const [messageText, setMessageText] = useState('');

  const { data: generalChat, isLoading: generalChatLoading } = useGeneralChat();
  const { data: messages } = useGeneralChatMessages();
  const sendMutation = useSendGeneralMessage();

  if (!user || user.role !== 'teacher') {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSendMessage = async () => {
    if (!messageText.trim() || !generalChat?.id) return;

    try {
      await sendMutation.mutateAsync({
        content: messageText,
      });
      setMessageText('');
    } catch (error) {
      logger.error('Failed to send message:', error);
    }
  };

  return (
    <SidebarProvider>
      <TeacherSidebar />
      <SidebarInset>
        <div className="flex flex-col h-screen bg-background">
          <div className="flex items-center justify-between border-b p-4">
            <div className="flex items-center gap-3">
              <SidebarTrigger />
              <div>
                <h1 className="text-xl font-semibold flex items-center gap-2">
                  <MessageSquare className="w-5 h-5" />
                  Сообщения
                </h1>
                <p className="text-sm text-muted-foreground">
                  {generalChat?.name || 'Общий чат'}
                </p>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {generalChatLoading ? (
              <div className="text-center text-muted-foreground py-8">Загрузка чата...</div>
            ) : !generalChat ? (
              <Card className="p-8 text-center">
                <MessageSquare className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                <p className="text-muted-foreground">Чата не найдено</p>
              </Card>
            ) : messages && messages.length > 0 ? (
              <div className="space-y-4">
                {messages.map((msg: any) => (
                  <div
                    key={msg.id}
                    className={`flex gap-3 ${msg.sender?.id === user.id ? 'justify-end' : ''}`}
                  >
                    <div
                      className={`max-w-xs px-4 py-2 rounded-lg ${
                        msg.sender?.id === user.id
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted'
                      }`}
                    >
                      <p className="text-sm font-medium">{msg.sender?.full_name || 'Аноним'}</p>
                      <p className="text-sm">{msg.content}</p>
                      <p className="text-xs opacity-70 mt-1">
                        {msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : 'Unknown time'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-muted-foreground py-8">Нет сообщений</div>
            )}
          </div>

          {generalChat && (
            <div className="border-t p-4">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={messageText}
                  onChange={(e) => setMessageText(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  placeholder="Напишите сообщение..."
                  className="flex-1 px-3 py-2 rounded-lg border border-input bg-background text-sm"
                />
                <Button
                  onClick={handleSendMessage}
                  disabled={sendMutation.isPending || !messageText.trim()}
                  className="px-6"
                >
                  {sendMutation.isPending ? 'Отправка...' : 'Отправить'}
                </Button>
              </div>
            </div>
          )}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
