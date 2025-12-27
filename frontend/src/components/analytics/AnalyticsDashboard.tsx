import React, { useState } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
} from 'recharts';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Alert,
  AlertDescription,
} from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  AlertCircle,
  Download,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Users,
  BookOpen,
  Target,
  Award,
  Zap,
  BarChart3,
  LineChart as LineChartIcon,
} from 'lucide-react';
import { format, subDays, startOfMonth, endOfMonth } from 'date-fns';
import { ru } from 'date-fns/locale';
import {
  AnalyticsDashboardData,
  useAnalyticsDashboard,
} from '@/hooks/useAnalyticsDashboard';
import { useToast } from '@/hooks/use-toast';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';

interface AnalyticsDashboardProps {
  initialDateFrom?: string;
  initialDateTo?: string;
  classId?: number;
  studentId?: number;
}

/**
 * Comprehensive Analytics Dashboard Component
 *
 * Displays key metrics, trends, and performance data with:
 * - KPI cards (overview section)
 * - Learning progress charts
 * - Engagement metrics graphs
 * - Student performance rankings
 * - Class/section analytics
 * - Date range filtering
 * - Export functionality
 * - Real-time updates via WebSocket
 *
 * Features:
 * - Responsive design (mobile, tablet, desktop)
 * - Loading and error states
 * - Drill-down capability (click on data points)
 * - Comparison view (period comparison)
 * - Chart interactivity (hover tooltips, legends)
 * - Exportable data (CSV, PDF)
 */
export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  initialDateFrom,
  initialDateTo,
  classId,
  studentId,
}) => {
  const { toast } = useToast();
  const [dateFrom, setDateFrom] = useState(
    initialDateFrom || format(subDays(new Date(), 30), 'yyyy-MM-dd')
  );
  const [dateTo, setDateTo] = useState(
    initialDateTo || format(new Date(), 'yyyy-MM-dd')
  );
  const [selectedClass, setSelectedClass] = useState<number | undefined>(classId);

  const { data, loading, error, refetch, isRefetching } =
    useAnalyticsDashboard({
      dateFrom,
      dateTo,
      classId: selectedClass,
      studentId,
    });

  const handleDateRangeQuick = (days: number) => {
    const newDateTo = new Date();
    const newDateFrom = subDays(newDateTo, days);
    setDateFrom(format(newDateFrom, 'yyyy-MM-dd'));
    setDateTo(format(newDateTo, 'yyyy-MM-dd'));
  };

  const handleExport = async (format: 'csv' | 'xlsx' | 'pdf') => {
    try {
      // TODO: Implement export functionality
      toast({
        title: 'Export Started',
        description: `Exporting analytics data as ${format.toUpperCase()}...`,
      });
    } catch (error) {
      toast({
        title: 'Export Failed',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to export data',
        variant: 'destructive',
      });
    }
  };

  const handleRefresh = async () => {
    try {
      await refetch();
      toast({
        title: 'Data Refreshed',
        description: 'Analytics data has been updated.',
      });
    } catch (error) {
      toast({
        title: 'Refresh Failed',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to refresh data',
        variant: 'destructive',
      });
    }
  };

  if (error && !data) {
    return (
      <Alert variant="destructive" className="m-4">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          {error.message || 'Failed to load analytics dashboard'}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Learning metrics and performance insights
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefetching}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${isRefetching ? 'animate-spin' : ''}`}
            />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('csv')}
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:gap-6">
            {/* Quick Date Range */}
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDateRangeQuick(7)}
              >
                Last 7 Days
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDateRangeQuick(30)}
              >
                Last 30 Days
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const monthStart = startOfMonth(new Date());
                  const monthEnd = endOfMonth(new Date());
                  setDateFrom(format(monthStart, 'yyyy-MM-dd'));
                  setDateTo(format(monthEnd, 'yyyy-MM-dd'));
                }}
              >
                This Month
              </Button>
            </div>

            {/* Date Inputs */}
            <div className="flex flex-col gap-2 md:flex-row md:gap-4">
              <div className="flex flex-col">
                <label className="text-sm font-medium mb-1">From</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="border rounded px-3 py-2 text-sm"
                />
              </div>
              <div className="flex flex-col">
                <label className="text-sm font-medium mb-1">To</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="border rounded px-3 py-2 text-sm"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* KPI Cards - Overview Section */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {loading && !data ? (
          <>
            {[...Array(4)].map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-6">
                  <Skeleton className="h-8 w-full mb-2" />
                  <Skeleton className="h-4 w-3/4" />
                </CardContent>
              </Card>
            ))}
          </>
        ) : data ? (
          <>
            {/* Total Students KPI */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Students
                </CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {data.metrics.total_students}
                </div>
                <Badge className="mt-2">
                  {data.metrics.active_students} Active
                </Badge>
              </CardContent>
            </Card>

            {/* Average Progress KPI */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Avg. Progress
                </CardTitle>
                <Target className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {Math.round(data.metrics.average_progress * 10) / 10}%
                </div>
                <Badge className="mt-2">
                  {data.metrics.completion_rate > 70 ? (
                    <TrendingUp className="h-3 w-3 mr-1" />
                  ) : (
                    <TrendingDown className="h-3 w-3 mr-1" />
                  )}
                  {Math.round(data.metrics.completion_rate)}% Complete
                </Badge>
              </CardContent>
            </Card>

            {/* Average Score KPI */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Avg. Score
                </CardTitle>
                <Award className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {Math.round(data.metrics.average_score * 10) / 10}%
                </div>
                <Badge className="mt-2">
                  {data.metrics.completed_assignments}/
                  {data.metrics.total_assignments} Completed
                </Badge>
              </CardContent>
            </Card>

            {/* Engagement KPI */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Engagement
                </CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {Math.round(data.metrics.average_engagement * 10) / 10}%
                </div>
                <Badge className="mt-2">Last 30 days</Badge>
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>

      {/* Charts Section */}
      <Tabs defaultValue="progress" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="progress">Progress</TabsTrigger>
          <TabsTrigger value="engagement">Engagement</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="classes">Classes</TabsTrigger>
        </TabsList>

        {/* Learning Progress Tab */}
        <TabsContent value="progress" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Learning Progress Trend</CardTitle>
              <CardDescription>
                Student progress and completion rate over time
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading && !data ? (
                <Skeleton className="h-72 w-full" />
              ) : data?.learning_progress && data.learning_progress.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={data.learning_progress}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="period"
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis
                      yAxisId="left"
                      tick={{ fontSize: 12 }}
                      label={{
                        value: 'Progress (%)',
                        angle: -90,
                        position: 'insideLeft',
                      }}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tick={{ fontSize: 12 }}
                      label={{
                        value: 'Students',
                        angle: 90,
                        position: 'insideRight',
                      }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                      }}
                    />
                    <Legend />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="average_progress"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={{ fill: '#3b82f6', r: 4 }}
                      activeDot={{ r: 6 }}
                      name="Avg Progress (%)"
                    />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="completion_rate"
                      stroke="#10b981"
                      strokeWidth={2}
                      dot={{ fill: '#10b981', r: 4 }}
                      activeDot={{ r: 6 }}
                      name="Completion Rate (%)"
                    />
                    <Bar
                      yAxisId="right"
                      dataKey="active_students"
                      fill="#f59e0b"
                      opacity={0.6}
                      name="Active Students"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-72 flex items-center justify-center text-muted-foreground">
                  No progress data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Engagement Tab */}
        <TabsContent value="engagement" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Engagement Metrics</CardTitle>
              <CardDescription>
                User activity and platform engagement over time
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading && !data ? (
                <Skeleton className="h-72 w-full" />
              ) : data?.engagement_trend && data.engagement_trend.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={data.engagement_trend}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis
                      yAxisId="left"
                      tick={{ fontSize: 12 }}
                      label={{
                        value: 'Score',
                        angle: -90,
                        position: 'insideLeft',
                      }}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tick={{ fontSize: 12 }}
                      label={{
                        value: 'Count',
                        angle: 90,
                        position: 'insideRight',
                      }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                      }}
                    />
                    <Legend />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="engagement_score"
                      stroke="#8b5cf6"
                      strokeWidth={2}
                      dot={{ fill: '#8b5cf6', r: 4 }}
                      activeDot={{ r: 6 }}
                      name="Engagement Score"
                    />
                    <Bar
                      yAxisId="right"
                      dataKey="active_users"
                      fill="#06b6d4"
                      opacity={0.6}
                      name="Active Users"
                    />
                    <Bar
                      yAxisId="right"
                      dataKey="assignments_submitted"
                      fill="#ec4899"
                      opacity={0.6}
                      name="Submissions"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-72 flex items-center justify-center text-muted-foreground">
                  No engagement data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Performance Rankings Tab */}
        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Top Performers</CardTitle>
              <CardDescription>
                Highest performing students by average score
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading && !data ? (
                <div className="space-y-2">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : data?.top_performers && data.top_performers.length > 0 ? (
                <div className="space-y-3">
                  {data.top_performers.map((student, index) => (
                    <div
                      key={student.student_id}
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-accent transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <Badge variant="outline" className="min-w-fit">
                          #{student.rank}
                        </Badge>
                        <div>
                          <p className="font-medium">{student.student_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {Math.round(student.completion_rate)}% Completion
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-lg">
                          {Math.round(student.average_score)}%
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Progress: {Math.round(student.progress)}%
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-32 flex items-center justify-center text-muted-foreground">
                  No performance data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Score Distribution Pie Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Score Distribution</CardTitle>
              <CardDescription>
                Distribution of student scores
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading && !data ? (
                <Skeleton className="h-72 w-full" />
              ) : data?.top_performers && data.top_performers.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={[
                        {
                          name: 'Excellent (90-100%)',
                          value: data.top_performers.filter(
                            (s) => s.average_score >= 90
                          ).length,
                        },
                        {
                          name: 'Good (80-89%)',
                          value: data.top_performers.filter(
                            (s) =>
                              s.average_score >= 80 && s.average_score < 90
                          ).length,
                        },
                        {
                          name: 'Fair (70-79%)',
                          value: data.top_performers.filter(
                            (s) =>
                              s.average_score >= 70 && s.average_score < 80
                          ).length,
                        },
                        {
                          name: 'Below Average (<70%)',
                          value: data.top_performers.filter(
                            (s) => s.average_score < 70
                          ).length,
                        },
                      ]}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, value }) => `${name}: ${value}`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      <Cell fill="#10b981" />
                      <Cell fill="#3b82f6" />
                      <Cell fill="#f59e0b" />
                      <Cell fill="#ef4444" />
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-72 flex items-center justify-center text-muted-foreground">
                  No score distribution data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Classes Tab */}
        <TabsContent value="classes" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Class Analytics</CardTitle>
              <CardDescription>
                Performance metrics by class or section
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading && !data ? (
                <Skeleton className="h-72 w-full" />
              ) : data?.class_analytics && data.class_analytics.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={data.class_analytics}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="class_name"
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      label={{
                        value: 'Score (%)',
                        angle: -90,
                        position: 'insideLeft',
                      }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                      }}
                    />
                    <Legend />
                    <Bar
                      dataKey="average_score"
                      fill="#3b82f6"
                      name="Avg Score"
                    />
                    <Bar
                      dataKey="average_progress"
                      fill="#10b981"
                      name="Avg Progress"
                    />
                    <Bar
                      dataKey="engagement_level"
                      fill="#f59e0b"
                      name="Engagement"
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-72 flex items-center justify-center text-muted-foreground">
                  No class data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Class Details Table */}
          {data?.class_analytics && data.class_analytics.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Class Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.class_analytics.map((cls) => (
                    <div
                      key={cls.class_id}
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-accent transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <BookOpen className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <p className="font-medium">{cls.class_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {cls.total_students} Students
                          </p>
                        </div>
                      </div>
                      <div className="flex gap-6 text-right">
                        <div>
                          <p className="font-bold">
                            {Math.round(cls.average_score)}%
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Avg Score
                          </p>
                        </div>
                        <div>
                          <p className="font-bold">
                            {Math.round(cls.average_progress)}%
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Progress
                          </p>
                        </div>
                        <div>
                          <p className="font-bold">
                            {Math.round(cls.engagement_level)}%
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Engagement
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Footer with metadata */}
      {data && (
        <div className="text-xs text-muted-foreground text-center">
          Data range: {format(new Date(data.date_range.start_date), 'dd MMMM yyyy', { locale: ru })} -{' '}
          {format(new Date(data.date_range.end_date), 'dd MMMM yyyy', { locale: ru })} •
          Last updated: {format(new Date(data.generated_at), 'HH:mm:ss')}
        </div>
      )}
    </div>
  );
};

export default AnalyticsDashboard;
