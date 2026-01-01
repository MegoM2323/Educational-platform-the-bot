import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, GraduationCap, BookOpen, Activity } from 'lucide-react';
import { adminAPI } from '@/integrations/api/adminAPI';
import StudentSection from '@/components/admin/StudentSection';
import TeacherSection from '@/components/admin/TeacherSection';
import TutorSection from '@/components/admin/TutorSection';
import ParentSection from '@/components/admin/ParentSection';

interface StatCard {
  title: string;
  value: number | string;
  icon: React.ReactNode;
}

export default function AccountManagement() {
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
      if (response?.success && response?.data) {
        // Backend returns {success: true, data: {...}} which is wrapped by adminAPI
        // So response.data is already the stats data
        // Handle multiple possible structures: response.data.data or response.data directly
        const rawData = response.data as any;
        const statsData = rawData?.data || rawData || {};
        setStats({
          total_users: statsData?.total_users ?? 0,
          total_students: statsData?.total_students ?? 0,
          total_teachers: statsData?.total_teachers ?? 0,
          total_tutors: statsData?.total_tutors ?? 0,
          total_parents: statsData?.total_parents ?? 0,
          active_today: statsData?.active_today ?? 0,
        });
      }
    } catch (error) {
      // Не критично, статистика опциональна
      console.error('Failed to load stats:', error);
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

      {/* 4 карточки управления - Студенты, Преподаватели, Тьютеры, Родители */}
      <div className="grid grid-cols-1 gap-6">
        <StudentSection onUpdate={loadStats} />
        <TeacherSection onUpdate={loadStats} />
        <TutorSection onUpdate={loadStats} />
        <ParentSection onUpdate={loadStats} />
      </div>
    </div>
  );
}
