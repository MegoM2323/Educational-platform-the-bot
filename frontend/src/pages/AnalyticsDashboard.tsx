import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AnalyticsDashboard as AnalyticsDashboardComponent } from '@/components/analytics/AnalyticsDashboard';
import { useAuth } from '@/hooks/useAuth';
import { ErrorBoundary } from '@/components/ErrorBoundary';
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

  const handleAnalyticsError = (error: Error) => {
    // Log to error tracking service (e.g., Sentry)
    console.error('Analytics Dashboard Error:', error);

    // In production, send to error tracking service
    if (process.env.NODE_ENV === 'production') {
      // TODO: Send to error tracking service like Sentry
      // captureException(error, { tags: { component: 'AnalyticsDashboard' } });
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <ErrorBoundary
        onError={handleAnalyticsError}
        fallback={
          <div className="min-h-screen flex items-center justify-center p-4">
            <Card className="w-full max-w-md p-6 text-center">
              <div className="flex flex-col items-center space-y-4">
                <div className="w-16 h-16 bg-destructive/10 rounded-full flex items-center justify-center">
                  <AlertCircle className="w-8 h-8 text-destructive" />
                </div>

                <div className="space-y-2">
                  <h2 className="text-xl font-semibold">Failed to Load Analytics</h2>
                  <p className="text-muted-foreground">
                    The analytics dashboard encountered an error. Please try refreshing the page.
                  </p>
                </div>
              </div>
            </Card>
          </div>
        }
      >
        <AnalyticsDashboardComponent
          initialDateFrom={dateFrom}
          initialDateTo={dateTo}
          classId={classId}
          studentId={studentId}
        />
      </ErrorBoundary>
    </div>
  );
};

export default AnalyticsDashboardPage;
