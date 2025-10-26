import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ErrorHandlingProvider } from "@/components/ErrorHandlingProvider";
import { AuthProvider } from "@/contexts/AuthContext";
import Index from "./pages/Index";
import Auth from "./pages/Auth";
import ApplicationForm from "./pages/ApplicationForm";
import ApplicationStatus from "./pages/ApplicationStatus";
import StudentDashboard from "./pages/dashboard/StudentDashboard";
import ParentDashboard from "./pages/dashboard/ParentDashboard";
import TeacherDashboard from "./pages/dashboard/TeacherDashboard";
import TutorDashboard from "./pages/dashboard/TutorDashboard";
import StudentMaterials from "./pages/dashboard/student/Materials";
import StudentGeneralChat from "./pages/dashboard/student/GeneralChat";
import TeacherMaterials from "./pages/dashboard/teacher/Materials";
import CreateMaterial from "./pages/dashboard/teacher/CreateMaterial";
import TeacherReports from "./pages/dashboard/teacher/Reports";
import TeacherGeneralChat from "./pages/dashboard/teacher/GeneralChat";
import TutorReports from "./pages/dashboard/tutor/Reports";
import ParentChildren from "./pages/dashboard/parent/Children";
import ParentStatistics from "./pages/dashboard/parent/Statistics";
import ParentReports from "./pages/dashboard/parent/Reports";
import Chat from "./pages/dashboard/Chat";
import Payments from "./pages/dashboard/Payments";
import NotFound from "./pages/NotFound";

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
          <BrowserRouter>
            <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/auth" element={<Auth />} />
          <Route path="/application" element={<ApplicationForm />} />
          <Route path="/application-status/:trackingToken" element={<ApplicationStatus />} />
          
          {/* Student Routes */}
          <Route path="/dashboard/student" element={
            <ProtectedRoute>
              <StudentDashboard />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/student/materials" element={
            <ProtectedRoute>
              <StudentMaterials />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/student/general-chat" element={
            <ProtectedRoute>
              <StudentGeneralChat />
            </ProtectedRoute>
          } />
          
          {/* Teacher Routes */}
          <Route path="/dashboard/teacher" element={
            <ProtectedRoute>
              <TeacherDashboard />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/materials" element={
            <ProtectedRoute>
              <TeacherMaterials />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/materials/create" element={
            <ProtectedRoute>
              <CreateMaterial />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/reports" element={
            <ProtectedRoute>
              <TeacherReports />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/general-chat" element={
            <ProtectedRoute>
              <TeacherGeneralChat />
            </ProtectedRoute>
          } />
          
          {/* Tutor Routes */}
          <Route path="/dashboard/tutor" element={
            <ProtectedRoute>
              <TutorDashboard />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/tutor/reports" element={
            <ProtectedRoute>
              <TutorReports />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/tutor/chat" element={
            <ProtectedRoute>
              <Chat />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/tutor/payments" element={
            <ProtectedRoute>
              <Payments />
            </ProtectedRoute>
          } />
          
          {/* Parent Routes */}
          <Route path="/dashboard/parent" element={
            <ProtectedRoute>
              <ParentDashboard />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/children" element={
            <ProtectedRoute>
              <ParentChildren />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/payments" element={
            <ProtectedRoute>
              <Payments />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/statistics" element={
            <ProtectedRoute>
              <ParentStatistics />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/reports" element={
            <ProtectedRoute>
              <ParentReports />
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
