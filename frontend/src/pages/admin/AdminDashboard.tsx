import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { Users, GraduationCap, BookOpen, Activity, LogOut } from 'lucide-react';
import StaffManagement from './StaffManagement';
import StudentManagement from './StudentManagement';
import ParentManagement from './ParentManagement';

interface StatCard {
  title: string;
  value: number | string;
  icon: React.ReactNode;
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [isLogoutLoading, setIsLogoutLoading] = useState(false);
  const [stats, setStats] = useState({
    total_users: 0,
    total_students: 0,
    total_teachers: 0,
    total_tutors: 0,
    total_parents: 0,
    active_today: 0,
  });

  useEffect(() => {
    // Загрузка статистики (когда будет готов endpoint)
    // Для сейчас используем простые значения
    loadStats();
  }, []);

  const loadStats = async () => {
    // TODO: Загружать статистику с backend когда будет endpoint
    // На данный момент это заглушка
    setStats({
      total_users: 0,
      total_students: 0,
      total_teachers: 0,
      total_tutors: 0,
      total_parents: 0,
      active_today: 0,
    });
  };

  const handleLogout = async () => {
    setIsLogoutLoading(true);
    try {
      await logout();
      toast.success('Вы вышли из системы');
      navigate('/auth');
    } catch (error) {
      console.error('Logout error:', error);
      toast.error('Ошибка при выходе');
    } finally {
      setIsLogoutLoading(false);
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
    <div className="container mx-auto p-4">
      {/* Заголовок */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Администратор</h1>
        <Button
          variant="destructive"
          onClick={handleLogout}
          disabled={isLogoutLoading}
        >
          <LogOut className="h-4 w-4 mr-2" />
          {isLogoutLoading ? 'Выход...' : 'Выйти'}
        </Button>
      </div>

      {/* Статистика */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
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

      {/* Основной контент с табами */}
      <Tabs defaultValue="students" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="students">Студенты</TabsTrigger>
          <TabsTrigger value="staff">Преподаватели и Тьюторы</TabsTrigger>
          <TabsTrigger value="parents">Родители</TabsTrigger>
        </TabsList>

        <TabsContent value="students" className="mt-6">
          <StudentManagement />
        </TabsContent>

        <TabsContent value="staff" className="mt-6">
          <StaffManagement />
        </TabsContent>

        <TabsContent value="parents" className="mt-6">
          <ParentManagement />
        </TabsContent>
      </Tabs>
    </div>
  );
}
