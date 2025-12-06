import { useAuth as useAuthContext } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { StudentProfileForm } from '@/components/profile/StudentProfileForm';
import { TeacherProfileForm } from '@/components/profile/TeacherProfileForm';
import { TutorProfileForm } from '@/components/profile/TutorProfileForm';
import { ParentProfileForm } from '@/components/profile/ParentProfileForm';
import { AvatarUpload } from '@/components/profile/AvatarUpload';
import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { ChevronLeft, RotateCcw } from 'lucide-react';
import {
  useStudentProfile,
  useUpdateStudentProfile,
  useUploadStudentAvatar,
  useTeacherProfile,
  useUpdateTeacherProfile,
  useUploadTeacherAvatar,
  useTutorProfile,
  useUpdateTutorProfile,
  useUploadTutorAvatar,
  useParentProfile,
  useUpdateParentProfile,
  useUploadParentAvatar,
  useReactivateProfile,
} from '@/hooks/useProfileAPI';

export const ProfilePage = () => {
  const navigate = useNavigate();
  const { user, isLoading: authLoading, isAuthenticated } = useAuthContext();

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner />
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    navigate('/auth');
    return null;
  }

  return <ProfilePageContent userRole={user.role} />;
};

interface ProfilePageContentProps {
  userRole: string;
}

const ProfilePageContent = ({ userRole }: ProfilePageContentProps) => {
  const navigate = useNavigate();
  const { user } = useAuthContext();

  // Render appropriate component based on user role
  // This ensures each role component only calls its own hooks
  switch (userRole) {
    case 'student':
      return <StudentProfilePageContent />;
    case 'teacher':
      return <TeacherProfilePageContent />;
    case 'tutor':
      return <TutorProfilePageContent />;
    case 'parent':
      return <ParentProfilePageContent />;
    default:
      return null;
  }
};

// Student profile component - only calls student profile hooks
const StudentProfilePageContent = () => {
  const navigate = useNavigate();
  const { user } = useAuthContext();

  const { data: profileData, isLoading } = useStudentProfile();
  const { mutate: updateProfile } = useUpdateStudentProfile();
  const { mutate: uploadAvatar } = useUploadStudentAvatar();
  const { mutate: reactivate, isPending: isReactivating } = useReactivateProfile();

  const handleProfileSubmit = async (data: Record<string, unknown>) => {
    return new Promise<void>((resolve, reject) => {
      updateProfile(data as any, {
        onSuccess: () => {
          resolve();
        },
        onError: (error: Error) => {
          reject(error);
        },
      });
    });
  };

  const handleAvatarUpload = async (file: File) => {
    return new Promise<void>((resolve, reject) => {
      uploadAvatar(file, {
        onSuccess: () => {
          resolve();
        },
        onError: (error: Error) => {
          reject(error);
        },
      });
    });
  };

  const handleReactivate = () => {
    reactivate(undefined);
  };

  return (
    <ProfileFormWrapper
      profileData={profileData}
      isLoading={isLoading}
      user={user}
      navigate={navigate}
      onSubmit={handleProfileSubmit}
      onAvatarUpload={handleAvatarUpload}
      FormComponent={StudentProfileForm}
      onReactivate={handleReactivate}
      isReactivating={isReactivating}
    />
  );
};

// Teacher profile component - only calls teacher profile hooks
const TeacherProfilePageContent = () => {
  const navigate = useNavigate();
  const { user } = useAuthContext();

  const { data: profileData, isLoading } = useTeacherProfile();
  const { mutate: updateProfile } = useUpdateTeacherProfile();
  const { mutate: uploadAvatar } = useUploadTeacherAvatar();
  const { mutate: reactivate, isPending: isReactivating } = useReactivateProfile();

  const handleProfileSubmit = async (data: Record<string, unknown>) => {
    return new Promise<void>((resolve, reject) => {
      updateProfile(data as any, {
        onSuccess: () => {
          resolve();
        },
        onError: (error: Error) => {
          reject(error);
        },
      });
    });
  };

  const handleAvatarUpload = async (file: File) => {
    return new Promise<void>((resolve, reject) => {
      uploadAvatar(file, {
        onSuccess: () => {
          resolve();
        },
        onError: (error: Error) => {
          reject(error);
        },
      });
    });
  };

  const handleReactivate = () => {
    reactivate(undefined);
  };

  return (
    <ProfileFormWrapper
      profileData={profileData}
      isLoading={isLoading}
      user={user}
      navigate={navigate}
      onSubmit={handleProfileSubmit}
      onAvatarUpload={handleAvatarUpload}
      FormComponent={TeacherProfileForm}
      onReactivate={handleReactivate}
      isReactivating={isReactivating}
    />
  );
};

// Tutor profile component - only calls tutor profile hooks
const TutorProfilePageContent = () => {
  const navigate = useNavigate();
  const { user } = useAuthContext();

  const { data: profileData, isLoading } = useTutorProfile();
  const { mutate: updateProfile } = useUpdateTutorProfile();
  const { mutate: uploadAvatar } = useUploadTutorAvatar();
  const { mutate: reactivate, isPending: isReactivating } = useReactivateProfile();

  const handleProfileSubmit = async (data: Record<string, unknown>) => {
    return new Promise<void>((resolve, reject) => {
      updateProfile(data as any, {
        onSuccess: () => {
          resolve();
        },
        onError: (error: Error) => {
          reject(error);
        },
      });
    });
  };

  const handleAvatarUpload = async (file: File) => {
    return new Promise<void>((resolve, reject) => {
      uploadAvatar(file, {
        onSuccess: () => {
          resolve();
        },
        onError: (error: Error) => {
          reject(error);
        },
      });
    });
  };

  const handleReactivate = () => {
    reactivate(undefined);
  };

  return (
    <ProfileFormWrapper
      profileData={profileData}
      isLoading={isLoading}
      user={user}
      navigate={navigate}
      onSubmit={handleProfileSubmit}
      onAvatarUpload={handleAvatarUpload}
      FormComponent={TutorProfileForm}
      onReactivate={handleReactivate}
      isReactivating={isReactivating}
    />
  );
};

// Parent profile component - only calls parent profile hooks
const ParentProfilePageContent = () => {
  const navigate = useNavigate();
  const { user } = useAuthContext();

  const { data: profileData, isLoading } = useParentProfile();
  const { mutate: updateProfile } = useUpdateParentProfile();
  const { mutate: uploadAvatar } = useUploadParentAvatar();
  const { mutate: reactivate, isPending: isReactivating } = useReactivateProfile();

  const handleProfileSubmit = async (data: Record<string, unknown>) => {
    return new Promise<void>((resolve, reject) => {
      updateProfile(data as any, {
        onSuccess: () => {
          resolve();
        },
        onError: (error: Error) => {
          reject(error);
        },
      });
    });
  };

  const handleAvatarUpload = async (file: File) => {
    return new Promise<void>((resolve, reject) => {
      uploadAvatar(file, {
        onSuccess: () => {
          resolve();
        },
        onError: (error: Error) => {
          reject(error);
        },
      });
    });
  };

  const handleReactivate = () => {
    reactivate(undefined);
  };

  return (
    <ProfileFormWrapper
      profileData={profileData}
      isLoading={isLoading}
      user={user}
      navigate={navigate}
      onSubmit={handleProfileSubmit}
      onAvatarUpload={handleAvatarUpload}
      FormComponent={ParentProfileForm}
      onReactivate={handleReactivate}
      isReactivating={isReactivating}
    />
  );
};

// Shared wrapper component that renders the UI for all profile pages
interface ProfileFormWrapperProps {
  profileData: any;
  isLoading: boolean;
  user: any;
  navigate: any;
  onSubmit: (data: Record<string, unknown>) => Promise<void>;
  onAvatarUpload: (file: File) => Promise<void>;
  FormComponent: any;
  onReactivate?: () => void;
  isReactivating?: boolean;
}

const ProfileFormWrapper = ({
  profileData,
  isLoading,
  user,
  navigate,
  onSubmit,
  onAvatarUpload,
  FormComponent,
  onReactivate,
  isReactivating,
}: ProfileFormWrapperProps) => {
  const flattenProfileData = (data: any) => {
    if (!data) return null;

    const { user, profile } = data;
    if (!user) return null;

    return {
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      phone: user.phone || '',
      telegram: user.telegram || '',
      ...profile,
    };
  };

  const userFirstName = user?.first_name || '';
  const userLastName = user?.last_name || '';
  const initials = (userFirstName[0] + userLastName[0]).toUpperCase();
  const avatar_url = profileData?.user?.avatar_url;
  const isInactive = profileData?.user?.is_active === false;

  const flattenedData = flattenProfileData(profileData);

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6 flex items-center gap-4">
          <Button type="button"
            variant="outline"
            size="sm"
            onClick={() => navigate(-1)}
            aria-label="Вернуться на предыдущую страницу"
          >
            <ChevronLeft className="w-4 h-4 mr-2" />
            Назад
          </Button>
          <nav className="flex items-center gap-2 text-sm text-gray-600">
            <span>Профиль</span>
            <span>/</span>
            <span className="text-gray-900 font-medium">
              {userFirstName} {userLastName}
            </span>
          </nav>
          {isInactive && onReactivate && (
            <Button type="button"
              variant="outline"
              size="sm"
              onClick={onReactivate}
              disabled={isReactivating}
              className="ml-auto"
              aria-label="Reactivate profile"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              {isReactivating ? 'Reactivating...' : 'Reactivate'}
            </Button>
          )}
        </div>

        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Мой профиль</h1>
          <p className="text-gray-600">
            Здесь вы можете редактировать информацию о себе
          </p>
          {isInactive && (
            <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
              Ваш профиль неактивен. Нажмите кнопку "Reactivate" в навигации, чтобы активировать профиль.
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1">
            <div className="sticky top-4">
              <AvatarUpload
                currentAvatar={avatar_url}
                onAvatarUpload={onAvatarUpload}
                isLoading={isLoading}
                fallbackInitials={initials}
              />
            </div>
          </div>

          <div className="lg:col-span-2">
            {isLoading && !flattenedData ? (
              <div className="flex items-center justify-center h-96">
                <LoadingSpinner />
              </div>
            ) : !flattenedData ? (
              <div className="flex items-center justify-center h-96">
                <p className="text-gray-600">Ошибка: не удалось загрузить профиль</p>
              </div>
            ) : (
              <FormComponent
                initialData={flattenedData}
                onSubmit={onSubmit}
                isLoading={isLoading}
              />
            )}
          </div>
        </div>

        <div className="lg:hidden mt-8 pt-8 border-t border-gray-200">
          <p className="text-xs text-gray-500 text-center">
            На мобильном устройстве аватар и форма расположены вертикально
          </p>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
