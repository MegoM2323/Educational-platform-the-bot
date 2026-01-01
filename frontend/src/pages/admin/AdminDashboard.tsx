import { useState, useEffect } from 'react';
import { logger } from '@/utils/logger';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Users, GraduationCap, BookOpen, Activity, Calendar, MessageSquare } from 'lucide-react';
import StudentSection from './sections/StudentSection';
import TeacherSection from './sections/TeacherSection';
import TutorSection from './sections/TutorSection';
import ParentSection from './sections/ParentSection';
import { adminAPI } from '@/integrations/api/adminAPI';
import { useToast } from '@/hooks/use-toast';

interface StatCard {
  title: string;
  value: number | string;
  icon: React.ReactNode;
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [stats, setStats] = useState({
    total_users: 0,
    total_students: 0,
    total_teachers: 0,
    total_tutors: 0,
    total_parents: 0,
    active_today: 0,
  });

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const response = await adminAPI.getUserStats();

      if (response.success && response.data) {
        logger.info('[AdminDashboard] Stats loaded:', response.data);
        setStats({
          total_users: response.data.total_users || 0,
          total_students: response.data.total_students || 0,
          total_teachers: response.data.total_teachers || 0,
          total_tutors: response.data.total_tutors || 0,
          total_parents: response.data.total_parents || 0,
          active_today: response.data.active_today || 0,
        });
      } else {
        logger.error('[AdminDashboard] Failed to load stats:', response.error);
        toast({
          variant: 'destructive',
          title: 'Ошибка загрузки статистики',
          description: response.error || 'Не удалось загрузить статистику пользователей',
        });
        // Оставляем нули если произошла ошибка
        setStats({
          total_users: 0,
          total_students: 0,
          total_teachers: 0,
          total_tutors: 0,
          total_parents: 0,
          active_today: 0,
        });
      }
    } catch (error) {
      logger.error('[AdminDashboard] Exception loading stats:', error);
      toast({
        variant: 'destructive',
        title: 'Ошибка загрузки статистики',
        description: 'Произошла непредвиденная ошибка при загрузке статистики',
      });
      // Оставляем нули если произошла ошибка
      setStats({
        total_users: 0,
        total_students: 0,
        total_teachers: 0,
        total_tutors: 0,
        total_parents: 0,
        active_today: 0,
      });
    }
  };

  const statCards: StatCard[] = [
    {
      title: 'Всего пользователей',
      value: stats.total_users,
      icon: <Users className="h-6 w-6 text-blue-500" />,
    },
    {
      title: 'Студентов',
      value: stats.total_students,
      icon: <GraduationCap className="h-6 w-6 text-green-500" />,
    },
    {
      title: 'Преподавателей',
      value: stats.total_teachers,
      icon: <BookOpen className="h-6 w-6 text-purple-500" />,
    },
    {
      title: 'Активных сегодня',
      value: stats.active_today,
      icon: <Activity className="h-6 w-6 text-red-500" />,
    },
  ];

  return (
    <div className="container mx-auto p-4 space-y-6">
      {/* Заголовок */}
      <div>
        <h1 className="text-3xl font-bold">Администратор</h1>
        <p className="text-muted-foreground mt-1">Управление пользователями и системой</p>
      </div>

      {/* Статистика */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat, index) => (
          <Card key={index}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="text-2xl font-bold">{stat.value}</div>
                <div>{stat.icon}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Секции управления (4 карточки) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <StudentSection onUpdate={loadStats} />
        <TeacherSection onUpdate={loadStats} />
        <TutorSection onUpdate={loadStats} />
        <ParentSection onUpdate={loadStats} />
      </div>

      {/* Навигация к другим разделам */}
      <Card>
        <CardHeader>
          <CardTitle>Другие разделы</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate('/admin/schedule')}
              className="flex items-center gap-2"
            >
              <Calendar className="h-4 w-4" />
              Расписание
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate('/admin/chats')}
              className="flex items-center gap-2"
            >
              <MessageSquare className="h-4 w-4" />
              Чаты
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
