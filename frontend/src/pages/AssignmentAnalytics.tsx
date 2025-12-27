import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AssignmentAnalytics as AnalyticsDashboard } from '@/components/assignments/AssignmentAnalytics';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowLeft, AlertCircle, Loader2 } from 'lucide-react';
import { assignmentsAPI } from '@/integrations/api/assignmentsAPI';

/**
 * AssignmentAnalytics Page
 *
 * Main page for displaying assignment analytics dashboard.
 * Only accessible to teachers/tutors who created the assignment.
 *
 * Route: `/assignments/:assignmentId/analytics`
 *
 * Features:
 * - Grade distribution with pie and bar charts
 * - Per-question difficulty analysis
 * - Submission timeline analysis
 * - Class average comparison
 * - Export to CSV
 * - Date range and student group filtering
 * - Responsive design for mobile/tablet/desktop
 */
export const AssignmentAnalyticsPage: React.FC = () => {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const navigate = useNavigate();

  const id = parseInt(assignmentId || '0', 10);

  // Fetch assignment details
  const {
    data: assignment,
    isLoading: assignmentLoading,
    error: assignmentError,
  } = useQuery({
    queryKey: ['assignment', id],
    queryFn: () => assignmentsAPI.getAssignment(id),
    enabled: id > 0,
  });

  // Check if user is authorized to view analytics (should be teacher/tutor who created it)
  useEffect(() => {
    // This would normally be checked by the API, but we can add client-side check here
    // For now, we'll rely on the API returning 403 if user is not authorized
  }, [assignment]);

  if (!id || id <= 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>Invalid assignment ID</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (assignmentLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
            <p className="text-sm text-muted-foreground">Loading assignment...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (assignmentError) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {assignmentError instanceof Error
              ? assignmentError.message
              : 'Failed to load assignment'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Back Button */}
        <div className="mb-8">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(-1)}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            <span className="hidden sm:inline">Back</span>
          </Button>
        </div>

        {/* Analytics Dashboard */}
        {assignment && (
          <AnalyticsDashboard
            assignmentId={id}
            assignmentTitle={assignment.title}
            onlyTeachers={true}
          />
        )}

        {/* Footer Note */}
        <div className="mt-12 border-t pt-8">
          <p className="text-xs text-muted-foreground text-center">
            Analytics data is cached for 5 minutes. Refresh the page to see latest updates.
          </p>
        </div>
      </div>
    </div>
  );
};

export default AssignmentAnalyticsPage;
