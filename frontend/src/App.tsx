import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ErrorHandlingProvider } from "@/components/ErrorHandlingProvider";
import { AuthProvider } from "@/contexts/AuthContext";
import { Suspense, lazy } from "react";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { ProtectedAdminRoute } from "@/components/ProtectedAdminRoute";
import StaffManagement from "@/pages/admin/StaffManagement";

// Импортируем критические компоненты напрямую
import Index from "./pages/Index";
import Auth from "./pages/Auth";
import ApplicationForm from "./pages/ApplicationForm";
import ApplicationStatus from "./pages/ApplicationStatus";
import NotFound from "./pages/NotFound";
import ParentDashboard from "./pages/dashboard/ParentDashboard";
const ParentPaymentHistory = lazy(() => import("./pages/dashboard/parent/PaymentHistory"));
const ParentPaymentSuccess = lazy(() => import("./pages/dashboard/parent/PaymentSuccess"));

// Lazy load только тяжелые компоненты дашбордов
const StudentDashboard = lazy(() => import("./pages/dashboard/StudentDashboard"));
const TeacherDashboard = lazy(() => import("./pages/dashboard/TeacherDashboard"));
const TutorDashboard = lazy(() => import("./pages/dashboard/TutorDashboard"));
const StudentMaterials = lazy(() => import("./pages/dashboard/student/Materials"));
const StudentSubjects = lazy(() => import("./pages/dashboard/student/Subjects"));
const StudentGeneralChat = lazy(() => import("./pages/dashboard/student/GeneralChat"));
const TeacherMaterials = lazy(() => import("./pages/dashboard/teacher/Materials"));
const CreateMaterial = lazy(() => import("./pages/dashboard/teacher/CreateMaterial"));
const TeacherReports = lazy(() => import("./pages/dashboard/teacher/Reports"));
const StudyPlans = lazy(() => import("./pages/dashboard/teacher/StudyPlans"));
const TeacherSubmissions = lazy(() => import("./pages/dashboard/teacher/Submissions"));
const TeacherGeneralChat = lazy(() => import("./pages/dashboard/teacher/GeneralChat"));
const AssignSubject = lazy(() => import("./pages/dashboard/teacher/AssignSubject"));
const TutorReports = lazy(() => import("./pages/dashboard/tutor/Reports"));
const TutorStudents = lazy(() => import("./pages/dashboard/tutor/Students"));
const TutorGeneralChat = lazy(() => import("./pages/dashboard/tutor/GeneralChat"));
const ParentChildren = lazy(() => import("./pages/dashboard/parent/Children"));
const ParentChildDetail = lazy(() => import("./pages/dashboard/parent/ChildDetail"));
const ParentStatistics = lazy(() => import("./pages/dashboard/parent/Statistics"));
const ParentReports = lazy(() => import("./pages/dashboard/parent/Reports"));
const Chat = lazy(() => import("./pages/dashboard/Chat"));

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
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/auth" element={<Auth />} />
          <Route path="/application" element={<ApplicationForm />} />
          <Route path="/application-status/:trackingToken" element={<ApplicationStatus />} />
          
          {/* Admin Routes */}
          <Route path="/admin/staff" element={
            <ProtectedAdminRoute>
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <StaffManagement />
              </Suspense>
            </ProtectedAdminRoute>
          } />
          
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
          <Route path="/dashboard/student/general-chat" element={
            import.meta.env.MODE === 'development' ? (
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <StudentGeneralChat />
              </Suspense>
            ) : (
              <ProtectedRoute requiredRole="student">
                <Suspense fallback={<LoadingSpinner size="lg" />}>
                  <StudentGeneralChat />
                </Suspense>
              </ProtectedRoute>
            )
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
          <Route path="/dashboard/teacher/general-chat" element={
            <ProtectedRoute requiredRole="teacher">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TeacherGeneralChat />
              </Suspense>
            </ProtectedRoute>
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
          <Route path="/dashboard/tutor/chat" element={
            <ProtectedRoute requiredRole="tutor">
              <Suspense fallback={<LoadingSpinner size="lg" />}>
                <TutorGeneralChat />
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
