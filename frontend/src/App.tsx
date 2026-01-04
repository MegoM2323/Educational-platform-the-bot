import { Toaster } from '@/components/ui/toaster';
import { Toaster as Sonner } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { ErrorHandlingProvider } from '@/components/ErrorHandlingProvider';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { Suspense, lazy, useEffect } from 'react';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { ProtectedAdminRoute } from '@/components/ProtectedAdminRoute';
import { ServiceWorkerUpdateNotification } from '@/components/ServiceWorkerUpdateNotification';
import { setAuthServiceAndNavigation } from '@/utils/api';
import { authService } from '@/services/authService';
import AdminLayout from '@/pages/admin/AdminLayout';
import AccountManagement from '@/pages/admin/AccountManagement';
import AdminSchedulePage from '@/pages/admin/AdminSchedulePage';
import AdminChatsPage from '@/pages/admin/AdminChatsPage';
import AdminBroadcastsPage from '@/pages/admin/AdminBroadcastsPage';
import SystemMonitoring from '@/pages/admin/SystemMonitoring';
import NotificationAnalytics from '@/pages/admin/NotificationAnalytics';
import NotificationTemplatesPage from '@/pages/admin/NotificationTemplatesPage';
import SystemSettings from '@/pages/admin/SystemSettings';

// Импортируем критические компоненты напрямую
import Index from './pages/Index';
import Auth from './pages/Auth';
import ApplicationForm from './pages/ApplicationForm';
import ApplicationStatus from './pages/ApplicationStatus';
import NotFound from './pages/NotFound';
import Unauthorized from './pages/Unauthorized';
import ParentDashboard from './pages/dashboard/ParentDashboard';
const ParentPaymentHistory = lazy(() => import('./pages/dashboard/parent/PaymentHistory'));
const ParentPaymentSuccess = lazy(() => import('./pages/dashboard/parent/PaymentSuccess'));
const ParentInvoices = lazy(() => import('./pages/dashboard/parent/InvoicesPage'));

// Import StudentDashboard directly to avoid React Router context timing issues
// Other dashboards can be lazy-loaded as they don't have the same initialization dependencies
import StudentDashboard from './pages/dashboard/StudentDashboard';
const TeacherDashboard = lazy(() => import('./pages/dashboard/TeacherDashboard'));
const TutorDashboard = lazy(() => import('./pages/dashboard/TutorDashboard'));
const StudentMaterials = lazy(() => import('./pages/dashboard/student/Materials'));
const StudentSubjects = lazy(() => import('./pages/dashboard/student/Subjects'));
const StudentAssignments = lazy(() => import('./pages/dashboard/student/Assignments'));
const TeacherMaterials = lazy(() => import('./pages/dashboard/teacher/Materials'));
const CreateMaterial = lazy(() => import('./pages/dashboard/teacher/CreateMaterial'));
const TeacherReports = lazy(() => import('./pages/dashboard/teacher/Reports'));
const StudyPlans = lazy(() => import('./pages/dashboard/teacher/StudyPlans'));
const TeacherSubmissions = lazy(() => import('./pages/dashboard/teacher/Submissions'));
const AssignSubject = lazy(() => import('./pages/dashboard/teacher/AssignSubject'));
const TeacherAssignments = lazy(() => import('./pages/dashboard/teacher/Assignments'));
const TeacherStudyPlanGenerator = lazy(
  () => import('./pages/dashboard/TeacherStudyPlanGeneratorPage')
);
const TutorReports = lazy(() => import('./pages/dashboard/tutor/Reports'));
const TutorStudents = lazy(() => import('./pages/dashboard/tutor/Students'));
const TutorInvoices = lazy(() => import('./pages/dashboard/tutor/InvoicesPage'));
const ParentChildren = lazy(() => import('./pages/dashboard/parent/Children'));
const ParentChildDetail = lazy(() => import('./pages/dashboard/parent/ChildDetail'));
const ParentStatistics = lazy(() => import('./pages/dashboard/parent/Statistics'));
const ParentReports = lazy(() => import('./pages/dashboard/parent/Reports'));
const Chat = lazy(() => import('./pages/dashboard/Chat'));

// Scheduling components
const StudentSchedulePage = lazy(() => import('./pages/dashboard/StudentSchedulePage'));
const TeacherSchedulePage = lazy(() => import('./pages/dashboard/TeacherSchedulePage'));
const TutorSchedulePage = lazy(() => import('./pages/dashboard/TutorSchedulePage'));
const ParentSchedulePage = lazy(() => import('./pages/dashboard/ParentSchedulePage'));

// Forum page
const Forum = lazy(() => import('./pages/dashboard/Forum'));

// Lesson Viewer
const LessonViewer = lazy(() => import('./pages/lessons/LessonViewer'));
const LessonViewerPage = lazy(() => import('./pages/dashboard/student/LessonViewerPage'));

// Knowledge Graph components
const KnowledgeGraphPage = lazy(() => import('./pages/dashboard/student/KnowledgeGraphPage'));
const ContentCreatorPage = lazy(() => import('./pages/dashboard/teacher/ContentCreatorPage'));
const LessonCreatorPage = lazy(() => import('./pages/dashboard/teacher/LessonCreatorPage'));
const GraphEditorPage = lazy(() => import('./pages/dashboard/teacher/GraphEditorPage'));
const ProgressViewerPage = lazy(() => import('./pages/dashboard/teacher/ProgressViewerPage'));

// Profile pages
const ProfilePage = lazy(() => import('./pages/profile/ProfilePage'));
const StudentProfilePage = lazy(() => import('./pages/profile/StudentProfilePage'));
const TeacherProfilePage = lazy(() => import('./pages/profile/TeacherProfilePage'));
const TutorProfilePage = lazy(() => import('./pages/profile/TutorProfilePage'));
const ParentProfilePage = lazy(() => import('./pages/profile/ParentProfilePage'));

// Settings pages
const NotificationSettings = lazy(() => import('./pages/settings/NotificationSettings'));

// Dashboard redirect component - redirects to role-specific dashboard
const DashboardRedirect = () => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingSpinner size="lg" text="Загрузка..." />;
  }

  if (!user) {
    return <Navigate to="/auth/signin" replace />;
  }

  // Redirect based on user role
  switch (user.role) {
    case 'student':
      return <Navigate to="/dashboard/student" replace />;
    case 'teacher':
      return <Navigate to="/dashboard/teacher" replace />;
    case 'tutor':
      return <Navigate to="/dashboard/tutor" replace />;
    case 'parent':
      return <Navigate to="/dashboard/parent" replace />;
    default:
      // Admin/staff users redirect to admin monitoring
      if (user.is_staff) {
        return <Navigate to="/admin/monitoring" replace />;
      }
      return <Navigate to="/auth/signin" replace />;
  }
};

// Dashboard assignments redirect - redirects to role-specific assignments page
const DashboardAssignmentsRedirect = () => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingSpinner size="lg" text="Загрузка..." />;
  }

  if (!user) {
    return <Navigate to="/auth/signin" replace />;
  }

  // Only student and teacher have assignments pages
  switch (user.role) {
    case 'student':
      return <Navigate to="/dashboard/student/assignments" replace />;
    case 'teacher':
      return <Navigate to="/dashboard/teacher/assignments" replace />;
    default:
      // For other roles, redirect to their main dashboard
      return <Navigate to="/dashboard" replace />;
  }
};

// Component to initialize API client with authService and navigate
// Must be inside BrowserRouter to use useNavigate hook
const ApiClientInitializer = ({ children }: { children: React.ReactNode }) => {
  const navigate = useNavigate();

  useEffect(() => {
    // Initialize API client with authService and navigate function
    // This enables automatic token refresh on 401 errors
    setAuthServiceAndNavigation(authService, navigate);
  }, [navigate]);

  return <>{children}</>;
};

// Configure React Query with default options
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60000, // 1 minute default stale time
      gcTime: 300000, // 5 minutes garbage collection time (was cacheTime)
      retry: 2,
      refetchOnWindowFocus: false,
      refetchOnMount: true,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 1,
    },
  },
});

const App = () => (
  <ErrorHandlingProvider>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <ServiceWorkerUpdateNotification />
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <ApiClientInitializer>
              <Routes>
                <Route path="/" element={<Index />} />
                {/* Auth Routes */}
                <Route path="/auth" element={<Navigate to="/auth/signin" replace />} />
                <Route path="/auth/signin" element={<Auth />} />
                <Route path="/auth/signup" element={<Navigate to="/application" replace />} />
                <Route path="/application" element={<ApplicationForm />} />
                <Route path="/application-status/:trackingToken" element={<ApplicationStatus />} />

                {/* Admin Routes with Layout */}
                <Route
                  path="/admin"
                  element={
                    <ProtectedAdminRoute>
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <AdminLayout />
                      </Suspense>
                    </ProtectedAdminRoute>
                  }
                >
                  <Route index element={<Navigate to="/admin/monitoring" replace />} />
                  <Route
                    path="monitoring"
                    element={
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <SystemMonitoring />
                      </Suspense>
                    }
                  />
                  <Route
                    path="accounts"
                    element={
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <AccountManagement />
                      </Suspense>
                    }
                  />
                  <Route
                    path="staff"
                    element={<Navigate to="/admin/accounts?tab=staff" replace />}
                  />
                  <Route
                    path="schedule"
                    element={
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <AdminSchedulePage />
                      </Suspense>
                    }
                  />
                  <Route
                    path="chats"
                    element={
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <AdminChatsPage />
                      </Suspense>
                    }
                  />
                  <Route
                    path="broadcasts"
                    element={
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <AdminBroadcastsPage />
                      </Suspense>
                    }
                  />
                  <Route
                    path="notifications"
                    element={
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <NotificationAnalytics />
                      </Suspense>
                    }
                  />
                  <Route
                    path="notification-templates"
                    element={
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <NotificationTemplatesPage />
                      </Suspense>
                    }
                  />
                  <Route
                    path="settings"
                    element={
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <SystemSettings />
                      </Suspense>
                    }
                  />

                  {/* Backward compatibility redirects */}
                  <Route
                    path="system-monitoring"
                    element={<Navigate to="/admin/monitoring" replace />}
                  />
                  <Route
                    path="account-management"
                    element={<Navigate to="/admin/accounts" replace />}
                  />
                  <Route path="audit" element={<Navigate to="/admin/monitoring" replace />} />
                  <Route path="jobs" element={<Navigate to="/admin/monitoring" replace />} />
                </Route>

                {/* Dashboard Routes - role-based redirects */}
                <Route path="/dashboard" element={<DashboardRedirect />} />
                <Route path="/dashboard/assignments" element={<DashboardAssignmentsRedirect />} />

                {/* Student Routes */}
                <Route
                  path="/dashboard/student"
                  element={
                    <ProtectedRoute requiredRole="student">
                      <StudentDashboard />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/student/subjects"
                  element={
                    <ProtectedRoute requiredRole="student">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <StudentSubjects />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/student/materials"
                  element={
                    import.meta.env.MODE === 'development' ? (
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <StudentMaterials />
                      </Suspense>
                    ) : (
                      <ProtectedRoute requiredRole="student">
                        <Suspense fallback={<LoadingSpinner size="lg" />}>
                          <StudentMaterials />
                        </Suspense>
                      </ProtectedRoute>
                    )
                  }
                />
                <Route
                  path="/dashboard/student/schedule"
                  element={
                    <ProtectedRoute requiredRole="student">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <StudentSchedulePage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/student/forum"
                  element={
                    <ProtectedRoute requiredRole="student">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <Forum />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/student/assignments"
                  element={
                    <ProtectedRoute requiredRole="student">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <StudentAssignments />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/student/knowledge-graph"
                  element={
                    <ProtectedRoute requiredRole="student">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <KnowledgeGraphPage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/student/lesson/:lessonId"
                  element={
                    <ProtectedRoute requiredRole="student">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <LessonViewerPage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/student/knowledge-graph/:graphId/lesson/:lessonId"
                  element={
                    <ProtectedRoute requiredRole="student">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <LessonViewer />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />

                {/* Teacher Routes */}
                <Route
                  path="/dashboard/teacher"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TeacherDashboard />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/materials"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TeacherMaterials />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/materials/create"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <CreateMaterial />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/reports"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TeacherReports />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/study-plans"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <StudyPlans />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                {/* Legacy teacher reports path support */}
                <Route
                  path="/teacher/reports"
                  element={
                    import.meta.env.MODE === 'development' ? (
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TeacherReports />
                      </Suspense>
                    ) : (
                      <ProtectedRoute requiredRole="teacher">
                        <Suspense fallback={<LoadingSpinner size="lg" />}>
                          <TeacherReports />
                        </Suspense>
                      </ProtectedRoute>
                    )
                  }
                />
                <Route
                  path="/dashboard/teacher/submissions/pending"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TeacherSubmissions />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/assign-subject"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <AssignSubject />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/schedule"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TeacherSchedulePage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/forum"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <Forum />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/assignments"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TeacherAssignments />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/study-plan-generator"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TeacherStudyPlanGenerator />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/content-creator"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <ContentCreatorPage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/lesson-creator"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <LessonCreatorPage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/lesson-creator/:lessonId"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <LessonCreatorPage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/graph-editor"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <GraphEditorPage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/teacher/progress"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <ProgressViewerPage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />

                {/* Tutor Routes */}
                <Route
                  path="/dashboard/tutor"
                  element={
                    <ProtectedRoute requiredRole="tutor">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TutorDashboard />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/tutor/students"
                  element={
                    <ProtectedRoute requiredRole="tutor">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TutorStudents />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/tutor/reports"
                  element={
                    <ProtectedRoute requiredRole="tutor">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TutorReports />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/tutor/forum"
                  element={
                    <ProtectedRoute requiredRole="tutor">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <Forum />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/tutor/schedule"
                  element={
                    <ProtectedRoute requiredRole="tutor">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TutorSchedulePage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/tutor/invoices"
                  element={
                    <ProtectedRoute requiredRole="tutor">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TutorInvoices />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />

                {/* Parent Routes */}
                <Route
                  path="/dashboard/parent"
                  element={
                    <ProtectedRoute requiredRole="parent">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <ParentDashboard />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/parent/children"
                  element={
                    <ProtectedRoute requiredRole="parent">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <ParentChildren />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/parent/children/:id"
                  element={
                    <ProtectedRoute requiredRole="parent">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <ParentChildDetail />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/parent/payment-history"
                  element={
                    <ProtectedRoute requiredRole="parent">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <ParentPaymentHistory />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/parent/payment-success"
                  element={
                    <ProtectedRoute requiredRole="parent">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <ParentPaymentSuccess />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/parent/invoices"
                  element={
                    <ProtectedRoute requiredRole="parent">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <ParentInvoices />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/parent/statistics"
                  element={
                    <ProtectedRoute requiredRole="parent">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <ParentStatistics />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/parent/reports"
                  element={
                    <ProtectedRoute requiredRole="parent">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <ParentReports />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/parent/forum"
                  element={
                    <ProtectedRoute requiredRole="parent">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <Forum />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/parent/schedule"
                  element={
                    <ProtectedRoute requiredRole="parent">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <ParentSchedulePage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />

                {/* Profile Routes - Available to all authenticated users */}
                <Route
                  path="/profile"
                  element={
                    <ProtectedRoute>
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <ProfilePage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/profile/student"
                  element={
                    <ProtectedRoute requiredRole="student">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <StudentProfilePage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/profile/teacher"
                  element={
                    <ProtectedRoute requiredRole="teacher">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TeacherProfilePage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/profile/tutor"
                  element={
                    <ProtectedRoute requiredRole="tutor">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <TutorProfilePage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/profile/parent"
                  element={
                    <ProtectedRoute requiredRole="parent">
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <ParentProfilePage />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />

                {/* Settings Routes - Available to all authenticated users */}
                <Route
                  path="/settings/notifications"
                  element={
                    <ProtectedRoute>
                      <Suspense fallback={<LoadingSpinner size="lg" />}>
                        <NotificationSettings />
                      </Suspense>
                    </ProtectedRoute>
                  }
                />

                {/* Unauthorized Route */}
                <Route path="/unauthorized" element={<Unauthorized />} />

                {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                <Route path="*" element={<NotFound />} />
              </Routes>
            </ApiClientInitializer>
          </BrowserRouter>
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  </ErrorHandlingProvider>
);

export default App;
