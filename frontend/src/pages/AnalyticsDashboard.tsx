import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AnalyticsDashboard as AnalyticsDashboardComponent } from '@/components/analytics/AnalyticsDashboard';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Loader2 } from 'lucide-react';

/**
 * Analytics Dashboard Page
 *
 * Main page for displaying comprehensive analytics dashboard.
 * Accessible to teachers, tutors, admins, and optionally parents
 * based on system configuration.
 *
 * Route: `/analytics`
 * Query params: ?dateFrom=YYYY-MM-DD&dateTo=YYYY-MM-DD&classId=123
 *
 * Features:
 * - Key performance indicators (KPIs)
 * - Learning progress trends
 * - Engagement metrics visualization
 * - Student performance rankings
 * - Class/section analytics
 * - Date range filtering with quick presets
 * - Period comparison
 * - Export to CSV/PDF
 * - Drill-down capability
 * - Real-time updates via WebSocket
 * - Responsive design for mobile/tablet/desktop
 *
 * Access Control:
 * - Teachers: Own classes and students
 * - Tutors: Assigned students
 * - Admins: All classes and students
 * - Parents: Own children (if enabled)
 */
export const AnalyticsDashboardPage: React.FC = () => {
  const { user, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Extract query parameters
  const dateFrom = searchParams.get('dateFrom') || undefined;
  const dateTo = searchParams.get('dateTo') || undefined;
  const classId = searchParams.get('classId')
    ? parseInt(searchParams.get('classId')!, 10)
    : undefined;
  const studentId = searchParams.get('studentId')
    ? parseInt(searchParams.get('studentId')!, 10)
    : undefined;

  // Check authorization
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/auth/signin');
      return;
    }

    // Check if user has access to analytics
    const hasAccess = ['teacher', 'tutor', 'admin'].includes(user?.role || '');
    if (!authLoading && !hasAccess) {
      navigate('/dashboard/student');
    }
  }, [user, authLoading, navigate]);

  // Show loading state while checking auth
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
            <p className="text-sm text-muted-foreground">
              Loading analytics dashboard...
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Show error if user not authorized
  if (user && !['teacher', 'tutor', 'admin'].includes(user.role || '')) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            You don't have permission to access the analytics dashboard.
            Only teachers, tutors, and administrators can view analytics.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <AnalyticsDashboardComponent
        initialDateFrom={dateFrom}
        initialDateTo={dateTo}
        classId={classId}
        studentId={studentId}
      />
    </div>
  );
};

export default AnalyticsDashboardPage;
