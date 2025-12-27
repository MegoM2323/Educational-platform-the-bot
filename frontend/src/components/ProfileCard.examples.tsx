/**
import { logger } from '@/utils/logger';
 * ProfileCard Component Examples
 *
 * This file contains usage examples for the ProfileCard component
 * showing how to use it for different user roles.
 */

import React from "react";
import ProfileCard, { ProfileCardProps } from "./ProfileCard";

/**
 * STUDENT PROFILE EXAMPLE
 *
 * Display a student's profile with learning progress and goals
 */
export const StudentProfileExample: React.FC = () => {
  const handleEditStudent = () => {
    logger.debug("Edit student profile");
  };

  const studentProps: ProfileCardProps = {
    userName: "Иван Петров",
    userEmail: "ivan.petrov@example.com",
    userRole: "student",
    avatarUrl: "https://api.example.com/avatars/ivan.jpg",
    profileData: {
      grade: "10А",
      learningGoal: "Подготовка к ЕГЭ по математике и физике",
      progressPercentage: 75.5,
      subjectsCount: 4,
    },
    onEdit: handleEditStudent,
  };

  return (
    <div className="p-4 max-w-md">
      <ProfileCard {...studentProps} />
    </div>
  );
};

/**
 * STUDENT PROFILE - WITHOUT AVATAR
 *
 * When avatar URL is not provided, component shows initials fallback
 */
export const StudentProfileNoAvatarExample: React.FC = () => {
  const studentProps: ProfileCardProps = {
    userName: "Мария Сидорова",
    userEmail: "maria.sidorova@example.com",
    userRole: "student",
    // No avatarUrl provided - will use initials fallback
    profileData: {
      grade: "11Б",
      learningGoal: "Улучшение знаний по английскому языку",
      progressPercentage: 62.3,
      subjectsCount: 5,
    },
    onEdit: () => logger.debug("Edit student"),
  };

  return (
    <div className="p-4 max-w-md">
      <ProfileCard {...studentProps} />
    </div>
  );
};

/**
 * TEACHER PROFILE EXAMPLE
 *
 * Display a teacher's profile with subjects and experience
 */
export const TeacherProfileExample: React.FC = () => {
  const handleEditTeacher = () => {
    logger.debug("Edit teacher profile");
  };

  const teacherProps: ProfileCardProps = {
    userName: "Алексей Иванов",
    userEmail: "alexey.ivanov@example.com",
    userRole: "teacher",
    avatarUrl: "https://api.example.com/avatars/alexey.jpg",
    profileData: {
      subjects: ["Математика", "Физика", "Информатика"],
      experience: 8,
      studentsCount: 45,
      materialsCount: 120,
    },
    onEdit: handleEditTeacher,
  };

  return (
    <div className="p-4 max-w-md">
      <ProfileCard {...teacherProps} />
    </div>
  );
};

/**
 * TEACHER PROFILE - WITH OBJECTS
 *
 * Subjects can also be passed as objects with id and name
 */
export const TeacherProfileWithSubjectsObjectsExample: React.FC = () => {
  const teacherProps: ProfileCardProps = {
    userName: "Ольга Петрова",
    userEmail: "olga.petrova@example.com",
    userRole: "teacher",
    profileData: {
      subjects: [
        { id: 1, name: "Биология" },
        { id: 2, name: "Химия" },
        { id: 3, name: "Экология" },
      ],
      experience: 12,
      studentsCount: 38,
      materialsCount: 95,
    },
  };

  return (
    <div className="p-4 max-w-md">
      <ProfileCard {...teacherProps} />
    </div>
  );
};

/**
 * TUTOR PROFILE EXAMPLE
 *
 * Display a tutor's profile with specialization and managed students
 */
export const TutorProfileExample: React.FC = () => {
  const handleEditTutor = () => {
    logger.debug("Edit tutor profile");
  };

  const tutorProps: ProfileCardProps = {
    userName: "Дарья Морозова",
    userEmail: "darya.morozova@example.com",
    userRole: "tutor",
    avatarUrl: "https://api.example.com/avatars/darya.jpg",
    profileData: {
      specialization: "Подготовка к ЕГЭ, репетиторство",
      experience: 5,
      studentsCount: 23,
      reportsCount: 18,
    },
    onEdit: handleEditTutor,
  };

  return (
    <div className="p-4 max-w-md">
      <ProfileCard {...tutorProps} />
    </div>
  );
};

/**
 * PARENT PROFILE EXAMPLE
 *
 * Display a parent's profile with children and subscription info
 */
export const ParentProfileExample: React.FC = () => {
  const handleEditParent = () => {
    logger.debug("Edit parent profile");
  };

  const parentProps: ProfileCardProps = {
    userName: "Елена Смирнова",
    userEmail: "elena.smirnova@example.com",
    userRole: "parent",
    avatarUrl: "https://api.example.com/avatars/elena.jpg",
    profileData: {
      childrenCount: 2,
      childrenNames: ["Даша Смирнова", "Коля Смирнов"],
      activeSubscriptions: 4,
      unreadReports: 3,
    },
    onEdit: handleEditParent,
  };

  return (
    <div className="p-4 max-w-md">
      <ProfileCard {...parentProps} />
    </div>
  );
};

/**
 * PARENT PROFILE - MINIMAL
 *
 * Parent profile with minimal information
 */
export const ParentProfileMinimalExample: React.FC = () => {
  const parentProps: ProfileCardProps = {
    userName: "Петр Николаев",
    userEmail: "petr.nikolaev@example.com",
    userRole: "parent",
    profileData: {
      childrenCount: 1,
    },
    onEdit: () => logger.debug("Edit parent"),
  };

  return (
    <div className="p-4 max-w-md">
      <ProfileCard {...parentProps} />
    </div>
  );
};

/**
 * RESPONSIVE EXAMPLE - ALL ROLES IN A GRID
 *
 * Shows how ProfileCard adapts to different screen sizes
 */
export const AllRolesGridExample: React.FC = () => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 p-6">
      {/* Student */}
      <ProfileCard
        userName="Иван Петров"
        userEmail="ivan@example.com"
        userRole="student"
        profileData={{
          grade: "10А",
          learningGoal: "Подготовка к ЕГЭ",
          progressPercentage: 75.5,
          subjectsCount: 4,
        }}
      />

      {/* Teacher */}
      <ProfileCard
        userName="Мария Сидорова"
        userEmail="maria@example.com"
        userRole="teacher"
        profileData={{
          subjects: ["Математика", "Физика"],
          experience: 8,
          studentsCount: 45,
          materialsCount: 120,
        }}
      />

      {/* Tutor */}
      <ProfileCard
        userName="Дарья Морозова"
        userEmail="darya@example.com"
        userRole="tutor"
        profileData={{
          specialization: "Подготовка к ЕГЭ",
          experience: 5,
          studentsCount: 23,
          reportsCount: 18,
        }}
      />

      {/* Parent */}
      <ProfileCard
        userName="Елена Смирнова"
        userEmail="elena@example.com"
        userRole="parent"
        profileData={{
          childrenCount: 2,
          childrenNames: ["Даша", "Коля"],
          activeSubscriptions: 4,
          unreadReports: 3,
        }}
      />
    </div>
  );
};

/**
 * INTEGRATION EXAMPLE - In a Dashboard
 *
 * How to integrate ProfileCard into a dashboard component
 */
export const DashboardIntegrationExample: React.FC = () => {
  const currentUser = {
    id: 1,
    name: "Иван Петров",
    email: "ivan@example.com",
    role: "student" as const,
    avatar: "https://api.example.com/avatars/ivan.jpg",
  };

  const handleProfileEdit = () => {
    // Navigate to edit profile page or open edit modal
    logger.debug("Opening profile edit...");
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-6">Мой профиль</h1>

        <ProfileCard
          userName={currentUser.name}
          userEmail={currentUser.email}
          userRole={currentUser.role}
          avatarUrl={currentUser.avatar}
          profileData={{
            grade: "10А",
            learningGoal: "Подготовка к ЕГЭ",
            progressPercentage: 75.5,
            subjectsCount: 4,
          }}
          onEdit={handleProfileEdit}
          className="max-w-2xl"
        />
      </div>

      {/* Other dashboard content below */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Dashboard sections */}
      </div>
    </div>
  );
};

/**
 * CUSTOM STYLING EXAMPLE
 *
 * Show how to apply custom styling via className prop
 */
export const CustomStyledProfileExample: React.FC = () => {
  return (
    <div className="p-6 bg-slate-50 rounded-lg">
      <ProfileCard
        userName="Кастомный стиль"
        userEmail="custom@example.com"
        userRole="teacher"
        profileData={{
          subjects: ["Предмет 1"],
          experience: 5,
          studentsCount: 20,
          materialsCount: 50,
        }}
        className="bg-white shadow-lg border-2 border-primary"
      />
    </div>
  );
};
