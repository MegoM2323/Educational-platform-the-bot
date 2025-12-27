import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ErrorHandlingProvider } from "@/components/ErrorHandlingProvider";
import { AuthProvider } from "@/contexts/AuthContext";
import { Suspense, lazy } from "react";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { ProtectedAdminRoute } from "@/components/ProtectedAdminRoute";
import { ServiceWorkerUpdateNotification } from "@/components/ServiceWorkerUpdateNotification";
import AdminLayout from "@/pages/admin/AdminLayout";
import AccountManagement from "@/pages/admin/AccountManagement";
import AdminSchedulePage from "@/pages/admin/AdminSchedulePage";
import AdminChatsPage from "@/pages/admin/AdminChatsPage";
import AdminBroadcastsPage from "@/pages/admin/AdminBroadcastsPage";
import SystemMonitoring from "@/pages/admin/SystemMonitoring";
import NotificationAnalytics from "@/pages/admin/NotificationAnalytics";
import NotificationTemplatesPage from "@/pages/admin/NotificationTemplatesPage";
import SystemSettings from "@/pages/admin/SystemSettings";

// Импортируем критические компоненты напрямую
import Index from "./pages/Index";
import Auth from "./pages/Auth";
import ApplicationForm from "./pages/ApplicationForm";
import ApplicationStatus from "./pages/ApplicationStatus";
import NotFound from "./pages/NotFound";
import Unauthorized from "./pages/Unauthorized";
import ParentDashboard from "./pages/dashboard/ParentDashboard";
const ParentPaymentHistory = lazy(() => import("./pages/dashboard/parent/PaymentHistory"));
const ParentPaymentSuccess = lazy(() => import("./pages/dashboard/parent/PaymentSuccess"));
const ParentInvoices = lazy(() => import("./pages/dashboard/parent/InvoicesPage"));

// Lazy load только тяжелые компоненты дашбордов
// Преимущество: эти чанки загружаются только когда пользователь переходит на соответствующие роли
const StudentDashboard = lazy(() => import(/* webpackChunkName: "student-dashboard" */ "./pages/dashboard/StudentDashboard"));
const TeacherDashboard = lazy(() => import(/* webpackChunkName: "teacher-dashboard" */ "./pages/dashboard/TeacherDashboard"));
const TutorDashboard = lazy(() => import(/* webpackChunkName: "tutor-dashboard" */ "./pages/dashboard/TutorDashboard"));
const StudentMaterials = lazy(() => import(/* webpackChunkName: "student-materials" */ "./pages/dashboard/student/Materials"));
const StudentSubjects = lazy(() => import(/* webpackChunkName: "student-subjects" */ "./pages/dashboard/student/Subjects"));
const StudentAssignments = lazy(() => import(/* webpackChunkName: "student-assignments" */ "./pages/dashboard/student/Assignments"));
const TeacherMaterials = lazy(() => import(/* webpackChunkName: "teacher-materials" */ "./pages/dashboard/teacher/Materials"));
const CreateMaterial = lazy(() => import(/* webpackChunkName: "create-material" */ "./pages/dashboard/teacher/CreateMaterial"));
const TeacherReports = lazy(() => import(/* webpackChunkName: "teacher-reports" */ "./pages/dashboard/teacher/Reports"));
const StudyPlans = lazy(() => import(/* webpackChunkName: "study-plans" */ "./pages/dashboard/teacher/StudyPlans"));
const TeacherSubmissions = lazy(() => import(/* webpackChunkName: "teacher-submissions" */ "./pages/dashboard/teacher/Submissions"));
const AssignSubject = lazy(() => import(/* webpackChunkName: "assign-subject" */ "./pages/dashboard/teacher/AssignSubject"));
const TeacherAssignments = lazy(() => import(/* webpackChunkName: "teacher-assignments" */ "./pages/dashboard/teacher/Assignments"));
const TeacherStudyPlanGenerator = lazy(() => import(/* webpackChunkName: "study-plan-generator" */ "./pages/dashboard/TeacherStudyPlanGeneratorPage"));
const TutorReports = lazy(() => import(/* webpackChunkName: "tutor-reports" */ "./pages/dashboard/tutor/Reports"));
const TutorStudents = lazy(() => import(/* webpackChunkName: "tutor-students" */ "./pages/dashboard/tutor/Students"));
const TutorInvoices = lazy(() => import(/* webpackChunkName: "tutor-invoices" */ "./pages/dashboard/tutor/InvoicesPage"));
const ParentChildren = lazy(() => import(/* webpackChunkName: "parent-children" */ "./pages/dashboard/parent/Children"));
const ParentChildDetail = lazy(() => import(/* webpackChunkName: "parent-child-detail" */ "./pages/dashboard/parent/ChildDetail"));
const ParentStatistics = lazy(() => import(/* webpackChunkName: "parent-stats" */ "./pages/dashboard/parent/Statistics"));
const ParentReports = lazy(() => import(/* webpackChunkName: "parent-reports" */ "./pages/dashboard/parent/Reports"));
const Chat = lazy(() => import(/* webpackChunkName: "chat" */ "./pages/dashboard/Chat"));

// Scheduling components
const StudentSchedulePage = lazy(() => import(/* webpackChunkName: "student-schedule" */ "./pages/dashboard/StudentSchedulePage"));
const TeacherSchedulePage = lazy(() => import(/* webpackChunkName: "teacher-schedule" */ "./pages/dashboard/TeacherSchedulePage"));
const TutorSchedulePage = lazy(() => import(/* webpackChunkName: "tutor-schedule" */ "./pages/dashboard/TutorSchedulePage"));
const ParentSchedulePage = lazy(() => import(/* webpackChunkName: "parent-schedule" */ "./pages/dashboard/ParentSchedulePage"));

// Forum page
const Forum = lazy(() => import(/* webpackChunkName: "forum" */ "./pages/dashboard/Forum"));

// Lesson Viewer
const LessonViewer = lazy(() => import(/* webpackChunkName: "lesson-viewer" */ "./pages/lessons/LessonViewer"));
const LessonViewerPage = lazy(() => import(/* webpackChunkName: "lesson-viewer-page" */ "./pages/dashboard/student/LessonViewerPage"));

// Knowledge Graph components
const KnowledgeGraphPage = lazy(() => import(/* webpackChunkName: "knowledge-graph" */ "./pages/dashboard/student/KnowledgeGraphPage"));
const ContentCreatorPage = lazy(() => import(/* webpackChunkName: "content-creator" */ "./pages/dashboard/teacher/ContentCreatorPage"));
const LessonCreatorPage = lazy(() => import(/* webpackChunkName: "lesson-creator" */ "./pages/dashboard/teacher/LessonCreatorPage"));
const GraphEditorPage = lazy(() => import(/* webpackChunkName: "graph-editor" */ "./pages/dashboard/teacher/GraphEditorPage"));
const ProgressViewerPage = lazy(() => import(/* webpackChunkName: "progress-viewer" */ "./pages/dashboard/teacher/ProgressViewerPage"));

// Profile pages
const ProfilePage = lazy(() => import(/* webpackChunkName: "profile" */ "./pages/profile/ProfilePage"));
const StudentProfilePage = lazy(() => import(/* webpackChunkName: "student-profile" */ "./pages/profile/StudentProfilePage"));
const TeacherProfilePage = lazy(() => import(/* webpackChunkName: "teacher-profile" */ "./pages/profile/TeacherProfilePage"));
const TutorProfilePage = lazy(() => import(/* webpackChunkName: "tutor-profile" */ "./pages/profile/TutorProfilePage"));
const ParentProfilePage = lazy(() => import(/* webpackChunkName: "parent-profile" */ "./pages/profile/ParentProfilePage"));

// Settings pages
const NotificationSettings = lazy(() => import(/* webpackChunkName: "notification-settings" */ "./pages/settings/NotificationSettings"));

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
            <Routes>
          <Route path="/" element={<Index />} />
          {/* Auth Routes */}
          <Route path="/auth" element={<Navigate to="/auth/signin" replace />} />
          <Route path="/auth/signin" element={<Auth />} />
          <Route path="/auth/signup" element={<Navigate to="/application" replace />} />
          <Route path="/application" element={<ApplicationForm />} />
          <Route path="/application-status/:trackingToken" element={<ApplicationStatus />} />
          
          {/* Admin Routes with Layout */}
          <Route path="/admin" element={
            <ProtectedAdminRoute>
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <AdminLayout />
              </Suspense>
            </ProtectedAdminRoute>
          }>
            <Route index element={<Navigate to="/admin/monitoring" replace />} />
            <Route path="monitoring" element={
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <SystemMonitoring />
              </Suspense>
            } />
            <Route path="accounts" element={
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <AccountManagement />
              </Suspense>
            } />
            <Route path="staff" element={<Navigate to="/admin/accounts?tab=staff" replace />} />
            <Route path="schedule" element={
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <AdminSchedulePage />
              </Suspense>
            } />
            <Route path="chats" element={
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <AdminChatsPage />
              </Suspense>
            } />
            <Route path="broadcasts" element={
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <AdminBroadcastsPage />
              </Suspense>
            } />
            <Route path="notifications" element={
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <NotificationAnalytics />
              </Suspense>
            } />
            <Route path="notification-templates" element={
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <NotificationTemplatesPage />
              </Suspense>
            } />
            <Route path="settings" element={
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <SystemSettings />
              </Suspense>
            } />
          </Route>

          {/* Student Routes */}
          <Route path="/dashboard/student" element={
            <ProtectedRoute requiredRole="student">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <StudentDashboard />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/student/subjects" element={
            <ProtectedRoute requiredRole="student">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <StudentSubjects />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/student/materials" element={
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
          } />
          <Route path="/dashboard/student/schedule" element={
            <ProtectedRoute requiredRole="student">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <StudentSchedulePage />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/student/forum" element={
            <ProtectedRoute requiredRole="student">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <Forum />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/student/assignments" element={
            <ProtectedRoute requiredRole="student">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <StudentAssignments />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/student/knowledge-graph" element={
            <ProtectedRoute requiredRole="student">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <KnowledgeGraphPage />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/student/lesson/:lessonId" element={
            <ProtectedRoute requiredRole="student">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <LessonViewerPage />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/student/knowledge-graph/:graphId/lesson/:lessonId" element={
            <ProtectedRoute requiredRole="student">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <LessonViewer />
              </Suspense>
            </ProtectedRoute>
          } />

          {/* Teacher Routes */}
          <Route path="/dashboard/teacher" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TeacherDashboard />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/materials" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TeacherMaterials />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/materials/create" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <CreateMaterial />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/reports" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TeacherReports />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/study-plans" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <StudyPlans />
              </Suspense>
            </ProtectedRoute>
          } />
          {/* Legacy teacher reports path support */}
          <Route path="/teacher/reports" element={
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
          } />
          <Route path="/dashboard/teacher/submissions/pending" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TeacherSubmissions />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/assign-subject" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <AssignSubject />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/schedule" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TeacherSchedulePage />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/forum" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <Forum />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/assignments" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TeacherAssignments />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/study-plan-generator" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TeacherStudyPlanGenerator />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/content-creator" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ContentCreatorPage />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/lesson-creator" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <LessonCreatorPage />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/lesson-creator/:lessonId" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <LessonCreatorPage />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/graph-editor" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <GraphEditorPage />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/progress" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ProgressViewerPage />
              </Suspense>
            </ProtectedRoute>
          } />

          {/* Tutor Routes */}
          <Route path="/dashboard/tutor" element={
            <ProtectedRoute requiredRole="tutor">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TutorDashboard />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/tutor/students" element={
            <ProtectedRoute requiredRole="tutor">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TutorStudents />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/tutor/reports" element={
            <ProtectedRoute requiredRole="tutor">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TutorReports />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/tutor/forum" element={
            <ProtectedRoute requiredRole="tutor">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <Forum />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/tutor/schedule" element={
            <ProtectedRoute requiredRole="tutor">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TutorSchedulePage />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/tutor/invoices" element={
            <ProtectedRoute requiredRole="tutor">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TutorInvoices />
              </Suspense>
            </ProtectedRoute>
          } />

          {/* Parent Routes */}
          <Route path="/dashboard/parent" element={
            <ProtectedRoute requiredRole="parent">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ParentDashboard />
              </Suspense>
            </ProtectedRoute>
          } />
          {/* Support trailing slash for parent dashboard */}
          <Route path="/dashboard/parent/" element={
            <ProtectedRoute requiredRole="parent">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ParentDashboard />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/children" element={
            <ProtectedRoute requiredRole="parent">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ParentChildren />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/children/:id" element={
            <ProtectedRoute requiredRole="parent">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ParentChildDetail />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/payment-history" element={
            <ProtectedRoute requiredRole="parent">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ParentPaymentHistory />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/payment-success" element={
            <ProtectedRoute requiredRole="parent">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ParentPaymentSuccess />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/invoices" element={
            <ProtectedRoute requiredRole="parent">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ParentInvoices />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/statistics" element={
            <ProtectedRoute requiredRole="parent">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ParentStatistics />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/reports" element={
            <ProtectedRoute requiredRole="parent">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ParentReports />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/forum" element={
            <ProtectedRoute requiredRole="parent">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <Forum />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/schedule" element={
            <ProtectedRoute requiredRole="parent">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ParentSchedulePage />
              </Suspense>
            </ProtectedRoute>
          } />

          {/* Profile Routes - Available to all authenticated users */}
          <Route path="/profile" element={
            <ProtectedRoute>
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ProfilePage />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/profile/student" element={
            <ProtectedRoute requiredRole="student">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <StudentProfilePage />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/profile/teacher" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TeacherProfilePage />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/profile/tutor" element={
            <ProtectedRoute requiredRole="tutor">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TutorProfilePage />
              </Suspense>
            </ProtectedRoute>
          } />
          <Route path="/profile/parent" element={
            <ProtectedRoute requiredRole="parent">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <ParentProfilePage />
              </Suspense>
            </ProtectedRoute>
          } />

          {/* Settings Routes - Available to all authenticated users */}
          <Route path="/settings/notifications" element={
            <ProtectedRoute>
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <NotificationSettings />
              </Suspense>
            </ProtectedRoute>
          } />

          {/* Unauthorized Route */}
          <Route path="/unauthorized" element={<Unauthorized />} />

          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  </ErrorHandlingProvider>
);

export default App;
