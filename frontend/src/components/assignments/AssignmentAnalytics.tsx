import React, { useState, useMemo, useCallback } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
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
  Calendar,
  Download,
  AlertCircle,
  Loader2,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Users,
  Clock,
  FileText,
} from 'lucide-react';
import { format, subDays, startOfMonth, endOfMonth } from 'date-fns';

interface AnalyticsData {
  assignment_id: number;
  assignment_title: string;
  max_score: number;
  statistics: {
    mean: number | null;
    median: number | null;
    mode: number | null;
    std_dev: number | null;
    min: number | null;
    max: number | null;
    q1: number | null;
    q2: number | null;
    q3: number | null;
    sample_size: number;
  };
  distribution: {
    buckets: {
      [key: string]: {
        label: string;
        count: number;
        percentage: number;
      };
    };
    total: number;
    pie_chart_data: Array<{
      label: string;
      value: number;
      percentage: number;
    }>;
  };
  submission_rate: {
    assigned_count: number;
    submitted_count: number;
    graded_count: number;
    late_count: number;
    submission_rate: number;
    grading_rate: number;
    late_rate: number;
  };
  comparison: {
    assignment_average: number | null;
    assignment_count: number;
    class_average: number | null;
    difference: number | null;
    performance: string;
  };
  generated_at: string;
}

interface QuestionAnalysisData {
  assignment_id: number;
  total_questions: number;
  questions: Array<{
    question_id: number;
    question_text: string;
    question_type: string;
    points: number;
    total_answers: number;
    correct_answers: number;
    wrong_answers: number;
    correct_rate: number;
    wrong_rate: number;
    difficulty_score: number;
  }>;
  difficulty_ranking: Array<{
    question_id: number;
    question_text: string;
    difficulty_score: number;
  }>;
  average_difficulty: number;
  generated_at: string;
}

interface TimeAnalysisData {
  assignment_id: number;
  submission_timing: {
    on_time_submissions: number;
    late_submissions: number;
    average_days_before_deadline: number | null;
    total_submissions: number;
  };
  late_submissions: {
    late_submission_count: number;
    late_submission_rate: number;
    average_days_late: number | null;
    most_days_late: number | null;
  };
  generated_at: string;
}

interface AssignmentAnalyticsProps {
  assignmentId: number;
  assignmentTitle?: string;
  onlyTeachers?: boolean;
}

const GRADE_COLORS = {
  A: '#10b981',
  B: '#3b82f6',
  C: '#f59e0b',
  D: '#ef4444',
  F: '#6b7280',
};

const DIFFICULTY_COLORS = {
  easy: '#10b981',
  medium: '#f59e0b',
  hard: '#ef4444',
};

/**
 * AssignmentAnalytics Component
 *
 * Displays comprehensive analytics dashboard for assignment performance.
 * Shows grade distribution, question difficulty, submission timeline, and class averages.
 *
 * @component
 * @example
 * ```tsx
 * <AssignmentAnalytics assignmentId={123} assignmentTitle="Quiz 1" />
 * ```
 */
export const AssignmentAnalytics: React.FC<AssignmentAnalyticsProps> = ({
  assignmentId,
  assignmentTitle = 'Assignment Analytics',
  onlyTeachers = true,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [questionData, setQuestionData] = useState<QuestionAnalysisData | null>(null);
  const [timeData, setTimeData] = useState<TimeAnalysisData | null>(null);
  const [dateRange, setDateRange] = useState<'week' | 'month' | 'all'>('all');
  const [studentGroup, setStudentGroup] = useState<string>('all');

  // Fetch analytics data
  React.useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        setError(null);

        // Simulate API call - replace with actual API when available
        const mockAnalytics: AnalyticsData = {
          assignment_id: assignmentId,
          assignment_title: assignmentTitle,
          max_score: 100,
          statistics: {
            mean: 78.5,
            median: 80,
            mode: 85,
            std_dev: 12.3,
            min: 45,
            max: 100,
            q1: 70,
            q2: 80,
            q3: 88,
            sample_size: 32,
          },
          distribution: {
            buckets: {
              A: {
                label: 'Excellent (90-100%)',
                count: 8,
                percentage: 25.0,
              },
              B: {
                label: 'Good (80-89%)',
                count: 12,
                percentage: 37.5,
              },
              C: {
                label: 'Satisfactory (70-79%)',
                count: 8,
                percentage: 25.0,
              },
              D: {
                label: 'Passing (60-69%)',
                count: 3,
                percentage: 9.4,
              },
              F: {
                label: 'Failing (<60%)',
                count: 1,
                percentage: 3.1,
              },
            },
            total: 32,
            pie_chart_data: [
              { label: 'A', value: 8, percentage: 25.0 },
              { label: 'B', value: 12, percentage: 37.5 },
              { label: 'C', value: 8, percentage: 25.0 },
              { label: 'D', value: 3, percentage: 9.4 },
              { label: 'F', value: 1, percentage: 3.1 },
            ],
          },
          submission_rate: {
            assigned_count: 35,
            submitted_count: 32,
            graded_count: 32,
            late_count: 5,
            submission_rate: 91.43,
            grading_rate: 100,
            late_rate: 15.63,
          },
          comparison: {
            assignment_average: 78.5,
            assignment_count: 32,
            class_average: 76.2,
            difference: 2.3,
            performance: 'Average',
          },
          generated_at: new Date().toISOString(),
        };

        const mockQuestion: QuestionAnalysisData = {
          assignment_id: assignmentId,
          total_questions: 5,
          questions: [
            {
              question_id: 1,
              question_text: 'What is the capital of France?',
              question_type: 'single_choice',
              points: 20,
              total_answers: 32,
              correct_answers: 30,
              wrong_answers: 2,
              correct_rate: 93.75,
              wrong_rate: 6.25,
              difficulty_score: 6.25,
            },
            {
              question_id: 2,
              question_text: 'List three major rivers in Europe',
              question_type: 'text',
              points: 20,
              total_answers: 32,
              correct_answers: 24,
              wrong_answers: 8,
              correct_rate: 75.0,
              wrong_rate: 25.0,
              difficulty_score: 25.0,
            },
            {
              question_id: 3,
              question_text: 'Select all countries in the EU',
              question_type: 'multiple_choice',
              points: 20,
              total_answers: 32,
              correct_answers: 18,
              wrong_answers: 14,
              correct_rate: 56.25,
              wrong_rate: 43.75,
              difficulty_score: 43.75,
            },
            {
              question_id: 4,
              question_text: 'When was the European Union formed?',
              question_type: 'single_choice',
              points: 20,
              total_answers: 32,
              correct_answers: 28,
              wrong_answers: 4,
              correct_rate: 87.5,
              wrong_rate: 12.5,
              difficulty_score: 12.5,
            },
            {
              question_id: 5,
              question_text: 'Explain the purpose of NATO',
              question_type: 'text',
              points: 20,
              total_answers: 32,
              correct_answers: 20,
              wrong_answers: 12,
              correct_rate: 62.5,
              wrong_rate: 37.5,
              difficulty_score: 37.5,
            },
          ],
          difficulty_ranking: [
            {
              question_id: 3,
              question_text: 'Select all countries in the EU',
              difficulty_score: 43.75,
            },
            {
              question_id: 5,
              question_text: 'Explain the purpose of NATO',
              difficulty_score: 37.5,
            },
            {
              question_id: 2,
              question_text: 'List three major rivers in Europe',
              difficulty_score: 25.0,
            },
            {
              question_id: 4,
              question_text: 'When was the European Union formed?',
              difficulty_score: 12.5,
            },
            {
              question_id: 1,
              question_text: 'What is the capital of France?',
              difficulty_score: 6.25,
            },
          ],
          average_difficulty: 25.0,
          generated_at: new Date().toISOString(),
        };

        const mockTime: TimeAnalysisData = {
          assignment_id: assignmentId,
          submission_timing: {
            on_time_submissions: 27,
            late_submissions: 5,
            average_days_before_deadline: 2.5,
            total_submissions: 32,
          },
          late_submissions: {
            late_submission_count: 5,
            late_submission_rate: 15.63,
            average_days_late: 1.2,
            most_days_late: 3,
          },
          generated_at: new Date().toISOString(),
        };

        setAnalyticsData(mockAnalytics);
        setQuestionData(mockQuestion);
        setTimeData(mockTime);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to load analytics data'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, [assignmentId, dateRange, studentGroup]);

  // Export data to CSV
  const handleExport = useCallback(() => {
    if (!analyticsData) return;

    const csvContent = [
      ['Assignment Analytics Report'],
      [
        `Assignment: ${analyticsData.assignment_title}`,
        `Generated: ${format(new Date(analyticsData.generated_at), 'PPP p')}`,
      ],
      [],
      ['Grade Distribution'],
      ['Grade', 'Count', 'Percentage'],
      ...Object.entries(analyticsData.distribution.buckets).map(([grade, data]) => [
        grade,
        data.count,
        data.percentage,
      ]),
      [],
      ['Statistics'],
      ['Metric', 'Value'],
      ['Mean', analyticsData.statistics.mean],
      ['Median', analyticsData.statistics.median],
      ['Min', analyticsData.statistics.min],
      ['Max', analyticsData.statistics.max],
      ['Std Dev', analyticsData.statistics.std_dev],
      [],
      ['Submission Metrics'],
      ['Metric', 'Value'],
      ['Submission Rate', analyticsData.submission_rate.submission_rate],
      ['Late Rate', analyticsData.submission_rate.late_rate],
      ['Grading Rate', analyticsData.submission_rate.grading_rate],
      [],
      ['Per-Question Analysis'],
      ['Question', 'Correct Rate', 'Difficulty'],
      ...(questionData?.questions || []).map((q) => [
        q.question_text,
        q.correct_rate,
        q.difficulty_score,
      ]),
    ]
      .map((row) => row.join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute(
      'download',
      `analytics_${assignmentId}_${format(new Date(), 'yyyy-MM-dd')}.csv`
    );
    link.click();
  }, [analyticsData, questionData, assignmentId]);

  if (loading) {
    return (
      <Card className="w-full">
        <CardContent className="flex items-center justify-center h-96">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Loading analytics...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!analyticsData || !questionData || !timeData) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>No analytics data available</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="w-full space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {analyticsData.assignment_title}
          </h1>
          <p className="text-sm text-muted-foreground mt-2">
            Generated {format(new Date(analyticsData.generated_at), 'PPP p')}
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            <span className="hidden sm:inline">Export to CSV</span>
            <span className="sm:hidden">Export</span>
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <label className="text-sm font-medium mb-2 block">Date Range</label>
          <Select value={dateRange} onValueChange={(value: any) => setDateRange(value)}>
            <SelectTrigger>
              <Calendar className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="week">Last 7 days</SelectItem>
              <SelectItem value="month">Last Month</SelectItem>
              <SelectItem value="all">All Time</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium mb-2 block">Student Group</label>
          <Select value={studentGroup} onValueChange={setStudentGroup}>
            <SelectTrigger>
              <Users className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Students</SelectItem>
              <SelectItem value="submitted">Submitted Only</SelectItem>
              <SelectItem value="not-submitted">Not Submitted</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Key Statistics Cards */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Mean Score"
          value={analyticsData.statistics.mean?.toFixed(1) || 'N/A'}
          subtext={`out of ${analyticsData.max_score}`}
          icon={<BarChart3 className="h-4 w-4 text-blue-500" />}
        />
        <StatCard
          label="Submission Rate"
          value={`${analyticsData.submission_rate.submission_rate.toFixed(1)}%`}
          subtext={`${analyticsData.submission_rate.submitted_count}/${analyticsData.submission_rate.assigned_count}`}
          icon={<Users className="h-4 w-4 text-green-500" />}
        />
        <StatCard
          label="Late Submissions"
          value={`${analyticsData.submission_rate.late_rate.toFixed(1)}%`}
          subtext={`${analyticsData.submission_rate.late_count} submissions`}
          icon={<Clock className="h-4 w-4 text-orange-500" />}
        />
        <StatCard
          label="Class Comparison"
          value={analyticsData.comparison.performance}
          subtext={
            analyticsData.comparison.difference !== null
              ? analyticsData.comparison.difference > 0
                ? `+${analyticsData.comparison.difference.toFixed(1)}`
                : `${analyticsData.comparison.difference.toFixed(1)}`
              : 'N/A'
          }
          icon={
            analyticsData.comparison.difference ? (
              analyticsData.comparison.difference > 0 ? (
                <TrendingUp className="h-4 w-4 text-green-500" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-500" />
              )
            ) : null
          }
        />
      </div>

      {/* Main Tabs */}
      <Tabs defaultValue="distribution" className="w-full">
        <TabsList className="grid w-full grid-cols-3 lg:grid-cols-5">
          <TabsTrigger value="distribution" className="text-xs sm:text-sm">
            Distribution
          </TabsTrigger>
          <TabsTrigger value="questions" className="text-xs sm:text-sm">
            Questions
          </TabsTrigger>
          <TabsTrigger value="timeline" className="text-xs sm:text-sm">
            Timeline
          </TabsTrigger>
          <TabsTrigger value="students" className="hidden sm:inline-flex text-xs sm:text-sm">
            Students
          </TabsTrigger>
          <TabsTrigger value="details" className="hidden lg:inline-flex text-xs sm:text-sm">
            Details
          </TabsTrigger>
        </TabsList>

        {/* Grade Distribution Tab */}
        <TabsContent value="distribution" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Grade Distribution</CardTitle>
              <CardDescription>
                Distribution of grades across {analyticsData.distribution.total} submissions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 lg:grid-cols-2">
                {/* Pie Chart */}
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={analyticsData.distribution.pie_chart_data}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ label, percentage }) =>
                          `${label} (${percentage.toFixed(1)}%)`
                        }
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {analyticsData.distribution.pie_chart_data.map((entry) => (
                          <Cell key={entry.label} fill={GRADE_COLORS[entry.label as keyof typeof GRADE_COLORS]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => `${value} students`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                {/* Bar Chart */}
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={Object.entries(analyticsData.distribution.buckets).map(
                        ([grade, data]) => ({
                          grade,
                          count: data.count,
                          percentage: data.percentage,
                        })
                      )}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="grade" />
                      <YAxis />
                      <Tooltip
                        formatter={(value) => [
                          value,
                          typeof value === 'number' && value > 1 ? 'Students' : 'Students',
                        ]}
                      />
                      <Bar dataKey="count" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Statistics Table */}
              <div className="mt-8">
                <h3 className="text-sm font-semibold mb-4">Descriptive Statistics</h3>
                <div className="grid gap-4 grid-cols-2 sm:grid-cols-4 lg:grid-cols-5">
                  <StatItem label="Mean" value={analyticsData.statistics.mean?.toFixed(2)} />
                  <StatItem label="Median" value={analyticsData.statistics.median?.toFixed(2)} />
                  <StatItem label="Mode" value={analyticsData.statistics.mode?.toFixed(2)} />
                  <StatItem label="Std Dev" value={analyticsData.statistics.std_dev?.toFixed(2)} />
                  <StatItem label="Sample" value={analyticsData.statistics.sample_size} />
                </div>
              </div>

              {/* Grade Buckets Breakdown */}
              <div className="mt-8">
                <h3 className="text-sm font-semibold mb-4">Grade Breakdown</h3>
                <div className="space-y-3">
                  {Object.entries(analyticsData.distribution.buckets).map(
                    ([grade, data]) => (
                      <div key={grade} className="flex items-center gap-4">
                        <div className="w-12 font-semibold text-center">{grade}</div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <div
                              className="h-2 rounded-full"
                              style={{
                                backgroundColor: GRADE_COLORS[grade as keyof typeof GRADE_COLORS],
                                width: `${data.percentage}%`,
                                minWidth: '4px',
                              }}
                            />
                          </div>
                        </div>
                        <div className="text-right text-sm">
                          <div className="font-medium">
                            {data.count} ({data.percentage.toFixed(1)}%)
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {data.label}
                          </div>
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Question Analysis Tab */}
        <TabsContent value="questions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Per-Question Analysis</CardTitle>
              <CardDescription>
                Difficulty ranking of {questionData.total_questions} questions
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Difficulty Ranking Chart */}
              <div className="h-96 mb-8">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={questionData.difficulty_ranking}
                    layout="vertical"
                    margin={{ top: 5, right: 30, left: 300 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" domain={[0, 100]} />
                    <YAxis
                      dataKey="question_text"
                      type="category"
                      width={290}
                      tick={{ fontSize: 12 }}
                    />
                    <Tooltip
                      formatter={(value) => [
                        `${Number(value).toFixed(2)}% wrong`,
                        'Difficulty',
                      ]}
                    />
                    <Bar dataKey="difficulty_score" fill="#f59e0b" radius={[0, 8, 8, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Detailed Question Table */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold">Detailed Question Metrics</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b">
                      <tr>
                        <th className="text-left py-2 px-2">Question</th>
                        <th className="text-right py-2 px-2">Correct</th>
                        <th className="text-right py-2 px-2">Wrong</th>
                        <th className="text-right py-2 px-2">Difficulty</th>
                        <th className="text-right py-2 px-2">Points</th>
                      </tr>
                    </thead>
                    <tbody>
                      {questionData.questions.map((question) => (
                        <tr key={question.question_id} className="border-b hover:bg-muted/50">
                          <td className="py-3 px-2">
                            <div className="text-sm font-medium line-clamp-2">
                              {question.question_text}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {question.question_type}
                            </div>
                          </td>
                          <td className="text-right py-3 px-2">
                            <span className="text-green-600 font-medium">
                              {question.correct_rate.toFixed(1)}%
                            </span>
                            <div className="text-xs text-muted-foreground">
                              {question.correct_answers}
                            </div>
                          </td>
                          <td className="text-right py-3 px-2">
                            <span className="text-red-600 font-medium">
                              {question.wrong_rate.toFixed(1)}%
                            </span>
                            <div className="text-xs text-muted-foreground">
                              {question.wrong_answers}
                            </div>
                          </td>
                          <td className="text-right py-3 px-2">
                            <div
                              className="inline-block px-2 py-1 rounded text-xs font-medium text-white"
                              style={{
                                backgroundColor:
                                  question.difficulty_score < 25
                                    ? DIFFICULTY_COLORS.easy
                                    : question.difficulty_score < 50
                                    ? DIFFICULTY_COLORS.medium
                                    : DIFFICULTY_COLORS.hard,
                              }}
                            >
                              {question.difficulty_score < 25
                                ? 'Easy'
                                : question.difficulty_score < 50
                                ? 'Medium'
                                : 'Hard'}
                            </div>
                          </td>
                          <td className="text-right py-3 px-2 font-medium">
                            {question.points}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Summary Stats */}
                <div className="grid gap-4 grid-cols-1 sm:grid-cols-3 mt-6">
                  <StatCard
                    label="Total Questions"
                    value={questionData.total_questions}
                    icon={<FileText className="h-4 w-4 text-blue-500" />}
                  />
                  <StatCard
                    label="Average Difficulty"
                    value={questionData.average_difficulty.toFixed(1)}
                    subtext="% wrong answers"
                    icon={<BarChart3 className="h-4 w-4 text-orange-500" />}
                  />
                  <StatCard
                    label="Most Difficult"
                    value={questionData.difficulty_ranking[0]?.question_id || 'N/A'}
                    subtext="Top question"
                    icon={<TrendingUp className="h-4 w-4 text-red-500" />}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Submission Timeline Tab */}
        <TabsContent value="timeline" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Submission Timeline</CardTitle>
              <CardDescription>
                Analysis of submission timing and late submissions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-8">
                {/* On-time vs Late */}
                <div>
                  <h3 className="text-sm font-semibold mb-4">On-Time vs Late Submissions</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={[
                          {
                            category: 'Submissions',
                            'On-Time': timeData.submission_timing.on_time_submissions,
                            'Late': timeData.submission_timing.late_submissions,
                          },
                        ]}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="category" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="On-Time" fill="#10b981" radius={[8, 8, 0, 0]} />
                        <Bar dataKey="Late" fill="#ef4444" radius={[8, 8, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 mt-6">
                    <StatCard
                      label="On-Time Submissions"
                      value={timeData.submission_timing.on_time_submissions}
                      subtext={`${(
                        (timeData.submission_timing.on_time_submissions /
                          timeData.submission_timing.total_submissions) *
                        100
                      ).toFixed(1)}%`}
                      icon={<TrendingUp className="h-4 w-4 text-green-500" />}
                    />
                    <StatCard
                      label="Late Submissions"
                      value={timeData.submission_timing.late_submissions}
                      subtext={`${(
                        (timeData.submission_timing.late_submissions /
                          timeData.submission_timing.total_submissions) *
                        100
                      ).toFixed(1)}%`}
                      icon={<TrendingDown className="h-4 w-4 text-red-500" />}
                    />
                  </div>
                </div>

                {/* Late Submission Details */}
                <div className="border-t pt-8">
                  <h3 className="text-sm font-semibold mb-4">Late Submission Details</h3>
                  <div className="grid gap-4 grid-cols-2 sm:grid-cols-3">
                    <StatCard
                      label="Late Rate"
                      value={`${timeData.late_submissions.late_submission_rate.toFixed(1)}%`}
                      icon={<Clock className="h-4 w-4 text-orange-500" />}
                    />
                    <StatCard
                      label="Avg Days Late"
                      value={timeData.late_submissions.average_days_late?.toFixed(1) || 'N/A'}
                      icon={<Clock className="h-4 w-4 text-orange-500" />}
                    />
                    <StatCard
                      label="Max Days Late"
                      value={timeData.late_submissions.most_days_late || 'N/A'}
                      icon={<Clock className="h-4 w-4 text-red-500" />}
                    />
                  </div>

                  {timeData.submission_timing.average_days_before_deadline && (
                    <div className="mt-6 p-4 bg-muted rounded-lg">
                      <p className="text-sm text-muted-foreground">
                        On-time submissions were submitted an average of{' '}
                        <span className="font-semibold text-foreground">
                          {timeData.submission_timing.average_days_before_deadline.toFixed(1)} days
                        </span>{' '}
                        before the deadline.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Students Tab */}
        <TabsContent value="students" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Submission Summary</CardTitle>
              <CardDescription>Student submission and grading status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 grid-cols-2 sm:grid-cols-3">
                <StatCard
                  label="Assigned"
                  value={analyticsData.submission_rate.assigned_count}
                  icon={<Users className="h-4 w-4 text-blue-500" />}
                />
                <StatCard
                  label="Submitted"
                  value={analyticsData.submission_rate.submitted_count}
                  subtext={`${analyticsData.submission_rate.submission_rate.toFixed(1)}%`}
                  icon={<Users className="h-4 w-4 text-green-500" />}
                />
                <StatCard
                  label="Graded"
                  value={analyticsData.submission_rate.graded_count}
                  subtext={`${analyticsData.submission_rate.grading_rate.toFixed(1)}%`}
                  icon={<Users className="h-4 w-4 text-green-500" />}
                />
              </div>

              <div className="mt-6">
                <h3 className="text-sm font-semibold mb-4">Submission Status</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Submitted</span>
                    <div className="flex-1 mx-4 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500"
                        style={{
                          width: `${analyticsData.submission_rate.submission_rate}%`,
                        }}
                      />
                    </div>
                    <span className="text-sm font-medium">
                      {analyticsData.submission_rate.submission_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Graded</span>
                    <div className="flex-1 mx-4 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500"
                        style={{
                          width: `${analyticsData.submission_rate.grading_rate}%`,
                        }}
                      />
                    </div>
                    <span className="text-sm font-medium">
                      {analyticsData.submission_rate.grading_rate.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Details Tab */}
        <TabsContent value="details" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Comparison with Class Average</CardTitle>
              <CardDescription>
                How this assignment compares to the overall class average
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {analyticsData.comparison.class_average ? (
                  <>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Assignment Average</span>
                        <span className="text-lg font-bold">
                          {analyticsData.comparison.assignment_average?.toFixed(1)}
                        </span>
                      </div>
                      <div
                        className="h-2 rounded-full bg-blue-500"
                        style={{
                          width: `${(
                            ((analyticsData.comparison.assignment_average || 0) /
                              analyticsData.max_score) *
                            100
                          ).toFixed(1)}%`,
                        }}
                      />
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Class Average</span>
                        <span className="text-lg font-bold">
                          {analyticsData.comparison.class_average?.toFixed(1)}
                        </span>
                      </div>
                      <div
                        className="h-2 rounded-full bg-gray-500"
                        style={{
                          width: `${(
                            ((analyticsData.comparison.class_average || 0) /
                              analyticsData.max_score) *
                            100
                          ).toFixed(1)}%`,
                        }}
                      />
                    </div>

                    <div className="border-t pt-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Difference</span>
                        <div className="flex items-center gap-2">
                          {analyticsData.comparison.difference !== null && (
                            <>
                              <span
                                className={`text-lg font-bold ${
                                  analyticsData.comparison.difference > 0
                                    ? 'text-green-600'
                                    : 'text-red-600'
                                }`}
                              >
                                {analyticsData.comparison.difference > 0 ? '+' : ''}
                                {analyticsData.comparison.difference.toFixed(1)}
                              </span>
                              {analyticsData.comparison.difference > 0 ? (
                                <TrendingUp className="h-4 w-4 text-green-600" />
                              ) : (
                                <TrendingDown className="h-4 w-4 text-red-600" />
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="mt-6 p-4 bg-muted rounded-lg">
                      <p className="text-sm font-medium mb-1">Performance Rating</p>
                      <p className="text-base font-semibold">
                        {analyticsData.comparison.performance}
                      </p>
                      <p className="text-xs text-muted-foreground mt-2">
                        This assignment is performing {analyticsData.comparison.performance.toLowerCase()} compared
                        to the class average.
                      </p>
                    </div>
                  </>
                ) : (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Insufficient data for class average comparison. Please ensure other assignments
                      have been graded.
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  subtext?: string;
  icon?: React.ReactNode;
}

/**
 * StatCard Component
 *
 * Displays a single statistic with label, value, and optional icon.
 *
 * @component
 */
const StatCard: React.FC<StatCardProps> = ({ label, value, subtext, icon }) => {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="text-2xl font-bold mt-2">{value}</p>
            {subtext && <p className="text-xs text-muted-foreground mt-1">{subtext}</p>}
          </div>
          {icon && <div className="ml-4 flex-shrink-0">{icon}</div>}
        </div>
      </CardContent>
    </Card>
  );
};

interface StatItemProps {
  label: string;
  value?: string | number;
}

/**
 * StatItem Component
 *
 * Displays a single statistic in a table-like format.
 *
 * @component
 */
const StatItem: React.FC<StatItemProps> = ({ label, value }) => {
  return (
    <div className="text-center">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-bold mt-1">{value || 'N/A'}</p>
    </div>
  );
};
