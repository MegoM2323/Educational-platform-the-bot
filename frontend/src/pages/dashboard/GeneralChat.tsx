import { GeneralChatForum } from '@/components/chat/GeneralChatForum';

export default function GeneralChat() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Общий форум</h1>
        <p className="text-muted-foreground">
          Общайтесь с преподавателями и другими студентами в общем форуме
        </p>
      </div>
      
      <GeneralChatForum />
    </div>
  );
}
