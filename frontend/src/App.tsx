import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Index from "./pages/Index";
import Auth from "./pages/Auth";
import StudentDashboard from "./pages/dashboard/StudentDashboard";
import ParentDashboard from "./pages/dashboard/ParentDashboard";
import TeacherDashboard from "./pages/dashboard/TeacherDashboard";
import TutorDashboard from "./pages/dashboard/TutorDashboard";
import StudentMaterials from "./pages/dashboard/student/Materials";
import TeacherReports from "./pages/dashboard/teacher/Reports";
import TutorReports from "./pages/dashboard/tutor/Reports";
import Chat from "./pages/dashboard/Chat";
import Payments from "./pages/dashboard/Payments";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/auth" element={<Auth />} />
          
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
          <Route path="/dashboard/student/chat" element={
            <ProtectedRoute>
              <Chat />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/student/payments" element={
            <ProtectedRoute>
              <Payments />
            </ProtectedRoute>
          } />
          
          {/* Teacher Routes */}
          <Route path="/dashboard/teacher" element={
            <ProtectedRoute>
              <TeacherDashboard />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/reports" element={
            <ProtectedRoute>
              <TeacherReports />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/chat" element={
            <ProtectedRoute>
              <Chat />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/teacher/payments" element={
            <ProtectedRoute>
              <Payments />
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
          <Route path="/dashboard/parent/chat" element={
            <ProtectedRoute>
              <Chat />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/parent/payments" element={
            <ProtectedRoute>
              <Payments />
            </ProtectedRoute>
          } />
          
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
