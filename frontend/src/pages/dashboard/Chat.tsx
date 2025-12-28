import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageCircle, Send, Search, Paperclip } from "lucide-react";
import { useState } from "react";

export default function Chat() {
  const [selectedChat, setSelectedChat] = useState(0);
  const [message, setMessage] = useState("");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Сообщения</h1>
        <p className="text-muted-foreground">Общайтесь с преподавателями и тьюторами</p>
      </div>

      <div className="grid md:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
        {/* Chat List */}
        <Card className="p-4 md:col-span-1">
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input placeholder="Поиск..." className="pl-10" />
          </div>
          <ScrollArea className="h-[calc(100%-60px)]">
            <div className="space-y-2">
              {chats.map((chat, index) => (
                <div
                  key={`chat-${chat.name}-${index}`}
                  onClick={() => setSelectedChat(index)}
                  className={`p-3 rounded-lg cursor-pointer transition-colors ${
                    selectedChat === index ? "bg-primary/10 border-primary" : "hover:bg-muted"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <Avatar className="w-10 h-10">
                      <AvatarFallback className="gradient-primary text-primary-foreground">
                        {chat.initials}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <div className="font-medium truncate">{chat.name}</div>
                        {chat.unread > 0 && (
                          <Badge variant="destructive" className="ml-2">{chat.unread}</Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground truncate">{chat.lastMessage}</p>
                      <div className="text-xs text-muted-foreground mt-1">{chat.time}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </Card>

        {/* Chat Window */}
        <Card className="p-6 md:col-span-2 flex flex-col">
          {/* Chat Header */}
          <div className="flex items-center gap-3 pb-4 border-b">
            <Avatar className="w-12 h-12">
              <AvatarFallback className="gradient-primary text-primary-foreground">
                {chats[selectedChat].initials}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <div className="font-bold">{chats[selectedChat].name}</div>
              <div className="text-sm text-muted-foreground">{chats[selectedChat].role}</div>
            </div>
          </div>

          {/* Messages */}
          <ScrollArea className="flex-1 py-4">
            <div className="space-y-4">
              {messages.map((msg, index) => (
                <div
                  key={`message-${msg.time}-${index}`}
                  className={`flex ${msg.isOwn ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[70%] p-3 rounded-lg ${
                      msg.isOwn
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    <p className="text-sm">{msg.text}</p>
                    <div
                      className={`text-xs mt-1 ${
                        msg.isOwn ? "text-primary-foreground/70" : "text-muted-foreground"
                      }`}
                    >
                      {msg.time}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>

          {/* Message Input */}
          <div className="flex gap-2 pt-4 border-t">
            <Button type="button" variant="outline" size="icon">
              <Paperclip className="w-4 h-4" />
            </Button>
            <Input
              placeholder="Введите сообщение..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === "Enter" && message.trim()) {
                  setMessage("");
                }
              }}
            />
            <Button type="button" className="gradient-primary">
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

const chats = [
  {
    name: "Иванова М.П.",
    role: "Преподаватель математики",
    initials: "ИМ",
    lastMessage: "Отличная работа с производными!",
    time: "10:30",
    unread: 2
  },
  {
    name: "Петров А.С.",
    role: "Преподаватель физики",
    initials: "ПА",
    lastMessage: "Не забудь про задание на завтра",
    time: "Вчера",
    unread: 0
  },
  {
    name: "Сидорова А.В.",
    role: "Тьютор",
    initials: "СА",
    lastMessage: "Давай обсудим твои цели на следующую неделю",
    time: "2 дня назад",
    unread: 1
  }
];

const messages = [
  {
    text: "Здравствуйте! Не могу разобраться с задачей №5",
    time: "10:25",
    isOwn: true
  },
  {
    text: "Привет! Давай разберем. Какой именно момент вызывает сложности?",
    time: "10:27",
    isOwn: false
  },
  {
    text: "Не понимаю, как правильно применить формулу производной в этом случае",
    time: "10:28",
    isOwn: true
  },
  {
    text: "Отличная работа с производными! Ты правильно все сделал, просто нужно еще раз внимательно посмотреть на коэффициенты.",
    time: "10:30",
    isOwn: false
  }
];
