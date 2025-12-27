/**
 * ReportsList Component - Usage Examples
 *
 * This file demonstrates how to use the ReportsList component in different scenarios
 */

import React, { useState } from 'react';
import { ReportsList, Report } from './ReportsList';
import { useToast } from '@/hooks/use-toast';

/**
 * Example 1: Basic usage with static reports
 */
export const BasicReportsListExample = () => {
  const mockReports: Report[] = [
    {
      id: 1,
      title: 'Месячный отчет о прогрессе',
      report_type: 'progress',
      status: 'draft',
      created_at: '2025-12-20T10:00:00Z',
      period_start: '2025-11-20',
      period_end: '2025-12-20',
      student_name: 'Иван Петров',
      description: 'Подробный отчет о прогрессе студента за месяц',
      owner_id: 1,
    },
    {
      id: 2,
      title: 'Отчет о поведении в классе',
      report_type: 'behavior',
      status: 'sent',
      created_at: '2025-12-15T10:00:00Z',
      student_name: 'Мария Сидорова',
      teacher_name: 'Петр Иванович',
      owner_id: 1,
    },
  ];

  return (
    <ReportsList
      reports={mockReports}
      userRole="teacher"
      currentUserId={1}
    />
  );
};

/**
 * Example 2: With callbacks for user interactions
 */
export const ReportsListWithCallbacksExample = () => {
  const { toast } = useToast();
  const [reports, setReports] = useState<Report[]>([
    {
      id: 1,
      title: 'Квартальный отчет',
      report_type: 'performance',
      status: 'read',
      created_at: '2025-12-20T10:00:00Z',
      student_name: 'Алексей Смирнов',
      owner_id: 1,
      attachment: '/files/report-q4.pdf',
    },
  ]);

  const handleView = async (report: Report) => {
    console.log('Viewing report:', report);
    // Navigate to report detail page or open modal
    // router.push(`/reports/${report.id}`);
  };

  const handleDownload = async (report: Report) => {
    console.log('Downloading report:', report);
    // Trigger file download from API
    // const response = await api.get(`/reports/${report.id}/download/`);
  };

  const handleDelete = async (report: Report) => {
    console.log('Deleting report:', report);
    // Delete from API
    // await api.delete(`/reports/${report.id}/`);
    setReports(prev => prev.filter(r => r.id !== report.id));
  };

  const handleShare = async (report: Report) => {
    console.log('Sharing report:', report);
    // Open share dialog or send to API
    // await api.post(`/reports/${report.id}/share/`);
  };

  return (
    <ReportsList
      reports={reports}
      onView={handleView}
      onDownload={handleDownload}
      onDelete={handleDelete}
      onShare={handleShare}
      userRole="teacher"
      currentUserId={1}
    />
  );
};

/**
 * Example 3: With API integration
 */
export const ReportsListWithAPIExample = () => {
  const [reports, setReports] = React.useState<Report[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const { toast } = useToast();

  React.useEffect(() => {
    const fetchReports = async () => {
      setIsLoading(true);
      try {
        // const { data } = await api.get('/reports/');
        // setReports(data);
        // Simulating API call
        setReports([
          {
            id: 1,
            title: 'Еженедельный отчет',
            report_type: 'progress',
            status: 'draft',
            created_at: new Date().toISOString(),
            student_name: 'Студент 1',
            owner_id: 1,
          },
        ]);
      } catch (error) {
        toast({
          title: 'Ошибка',
          description: 'Не удалось загрузить отчеты',
          variant: 'destructive',
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchReports();
  }, [toast]);

  const handleDelete = async (report: Report) => {
    try {
      // await api.delete(`/reports/${report.id}/`);
      setReports(prev => prev.filter(r => r.id !== report.id));
      toast({
        title: 'Успешно',
        description: 'Отчет удален',
      });
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: 'Не удалось удалить отчет',
        variant: 'destructive',
      });
    }
  };

  return (
    <ReportsList
      reports={reports}
      isLoading={isLoading}
      onDelete={handleDelete}
      userRole="teacher"
      currentUserId={1}
    />
  );
};

/**
 * Example 4: Different user roles
 */
export const ReportsListByRoleExample = () => {
  const mockReports: Report[] = [
    {
      id: 1,
      title: 'Отчет о прогрессе',
      report_type: 'progress',
      status: 'sent',
      created_at: '2025-12-20T10:00:00Z',
      student_name: 'Ученик Иванов',
      teacher_name: 'Учитель Петров',
      owner_id: 2,
    },
  ];

  // Teacher can create, delete, and share reports
  const TeacherView = () => (
    <ReportsList
      reports={mockReports}
      userRole="teacher"
      currentUserId={2}
      onDelete={() => {}}
      onShare={() => {}}
    />
  );

  // Parent can only view reports
  const ParentView = () => (
    <ReportsList
      reports={mockReports}
      userRole="parent"
      currentUserId={3}
    />
  );

  // Student can only view their own reports
  const StudentView = () => (
    <ReportsList
      reports={mockReports.filter(r => r.student_name === 'Ученик Иванов')}
      userRole="student"
      currentUserId={1}
    />
  );

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold mb-4">Вид учителя</h2>
        <TeacherView />
      </div>
      <div>
        <h2 className="text-lg font-semibold mb-4">Вид родителя</h2>
        <ParentView />
      </div>
      <div>
        <h2 className="text-lg font-semibold mb-4">Вид ученика</h2>
        <StudentView />
      </div>
    </div>
  );
};

/**
 * Example 5: With loading and empty states
 */
export const ReportsListWithStatesExample = () => {
  const [state, setState] = React.useState<'loading' | 'empty' | 'loaded'>('loading');
  const [reports, setReports] = React.useState<Report[]>([]);

  const simulateLoadingScenarios = () => {
    // Scenario 1: Loading state
    setState('loading');
    setTimeout(() => {
      // Scenario 2: Empty state
      setState('empty');
      setReports([]);
    }, 2000);

    setTimeout(() => {
      // Scenario 3: Loaded with data
      setState('loaded');
      setReports([
        {
          id: 1,
          title: 'Отчет 1',
          report_type: 'progress',
          status: 'draft',
          created_at: new Date().toISOString(),
          student_name: 'Студент 1',
          owner_id: 1,
        },
      ]);
    }, 4000);
  };

  React.useEffect(() => {
    simulateLoadingScenarios();
  }, []);

  return (
    <div className="space-y-4">
      <button
        onClick={simulateLoadingScenarios}
        className="px-4 py-2 bg-blue-600 text-white rounded"
      >
        Перезагрузить
      </button>

      <ReportsList
        reports={reports}
        isLoading={state === 'loading'}
        userRole="teacher"
        currentUserId={1}
      />

      <div className="text-sm text-gray-500">
        Состояние: {state === 'loading' ? 'Загрузка...' : state === 'empty' ? 'Пусто' : 'Загружено'}
      </div>
    </div>
  );
};
