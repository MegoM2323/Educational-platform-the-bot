import React, { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Mail, BookOpen, Award, Users, Target, Briefcase, Edit } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * User role type
 */
export type UserRole = 'student' | 'teacher' | 'tutor' | 'parent';

/**
 * Props for ProfileCard component
 */
export interface ProfileCardProps {
  /** User's full name */
  userName: string;
  /** User's email address */
  userEmail: string;
  /** User's role */
  userRole: UserRole;
  /** URL to user's avatar image (optional) */
  avatarUrl?: string;
  /** Role-specific profile data */
  profileData: Record<string, any>;
  /** Callback when edit button is clicked (optional) */
  onEdit?: () => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Get initials from user name
 */
const getInitials = (name: string): string => {
  return name
    .split(" ")
    .map((n) => n.charAt(0))
    .join("")
    .toUpperCase()
    .slice(0, 2);
};

/**
 * Get role display name and color variant
 */
const getRoleConfig = (
  role: UserRole
): { label: string; variant: "default" | "secondary" | "destructive" | "outline" } => {
  const configs: Record<UserRole, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
    student: { label: "Ученик", variant: "default" },
    teacher: { label: "Преподаватель", variant: "secondary" },
    tutor: { label: "Тьютор", variant: "destructive" },
    parent: { label: "Родитель", variant: "outline" },
  };
  return configs[role];
};

/**
 * Render role-specific profile information
 */
const renderRoleSpecificInfo = (role: UserRole, profileData: Record<string, any>) => {
  switch (role) {
    case "student":
      return (
        <div className="space-y-3">
          {profileData.grade && (
            <div className="flex items-start gap-3">
              <Target className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Класс</p>
                <p className="text-sm text-foreground">{profileData.grade}</p>
              </div>
            </div>
          )}
          {profileData.learningGoal && (
            <div className="flex items-start gap-3">
              <BookOpen className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Цель обучения</p>
                <p className="text-sm text-foreground">{profileData.learningGoal}</p>
              </div>
            </div>
          )}
          {profileData.progressPercentage !== undefined && (
            <div className="flex items-start gap-3">
              <Award className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1 w-full">
                <p className="text-sm font-medium text-muted-foreground mb-2">Прогресс обучения</p>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-300"
                    style={{ width: `${Math.min(profileData.progressPercentage, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {profileData.progressPercentage.toFixed(1)}% выполнено
                </p>
              </div>
            </div>
          )}
          {profileData.subjectsCount !== undefined && (
            <div className="flex items-start gap-3">
              <Users className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Предметы</p>
                <p className="text-sm text-foreground">{profileData.subjectsCount} предметов</p>
              </div>
            </div>
          )}
        </div>
      );

    case "teacher":
      return (
        <div className="space-y-3">
          {profileData.subjects && profileData.subjects.length > 0 && (
            <div className="flex items-start gap-3">
              <BookOpen className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground mb-2">Предметы</p>
                <div className="flex flex-wrap gap-2">
                  {profileData.subjects.map((subject: string | { id: number; name: string }, idx: number) => (
                    <Badge key={idx} variant="outline" className="text-xs">
                      {typeof subject === "string" ? subject : subject.name}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          )}
          {profileData.experience !== undefined && (
            <div className="flex items-start gap-3">
              <Briefcase className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Опыт работы</p>
                <p className="text-sm text-foreground">
                  {profileData.experience} {profileData.experience === 1 ? "год" : "лет"}
                </p>
              </div>
            </div>
          )}
          {profileData.studentsCount !== undefined && (
            <div className="flex items-start gap-3">
              <Users className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Ученики</p>
                <p className="text-sm text-foreground">{profileData.studentsCount} ученик(ов)</p>
              </div>
            </div>
          )}
          {profileData.materialsCount !== undefined && (
            <div className="flex items-start gap-3">
              <Award className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Материалы</p>
                <p className="text-sm text-foreground">{profileData.materialsCount} материалов</p>
              </div>
            </div>
          )}
        </div>
      );

    case "tutor":
      return (
        <div className="space-y-3">
          {profileData.specialization && (
            <div className="flex items-start gap-3">
              <BookOpen className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Специализация</p>
                <p className="text-sm text-foreground">{profileData.specialization}</p>
              </div>
            </div>
          )}
          {profileData.experience !== undefined && (
            <div className="flex items-start gap-3">
              <Briefcase className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Опыт работы</p>
                <p className="text-sm text-foreground">
                  {profileData.experience} {profileData.experience === 1 ? "год" : "лет"}
                </p>
              </div>
            </div>
          )}
          {profileData.studentsCount !== undefined && (
            <div className="flex items-start gap-3">
              <Users className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Управляемые ученики</p>
                <p className="text-sm text-foreground">{profileData.studentsCount} ученик(ов)</p>
              </div>
            </div>
          )}
          {profileData.reportsCount !== undefined && (
            <div className="flex items-start gap-3">
              <Award className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Отправленные отчеты</p>
                <p className="text-sm text-foreground">{profileData.reportsCount}</p>
              </div>
            </div>
          )}
        </div>
      );

    case "parent":
      return (
        <div className="space-y-3">
          {profileData.childrenCount !== undefined && (
            <div className="flex items-start gap-3">
              <Users className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Дети</p>
                <p className="text-sm text-foreground">
                  {profileData.childrenCount} {profileData.childrenCount === 1 ? "ребёнок" : "детей"}
                </p>
              </div>
            </div>
          )}
          {profileData.childrenNames && profileData.childrenNames.length > 0 && (
            <div className="flex items-start gap-3">
              <Award className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground mb-2">Имена детей</p>
                <div className="flex flex-wrap gap-2">
                  {profileData.childrenNames.map((name: string, idx: number) => (
                    <Badge key={idx} variant="outline" className="text-xs">
                      {name}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          )}
          {profileData.activeSubscriptions !== undefined && (
            <div className="flex items-start gap-3">
              <Briefcase className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Активные подписки</p>
                <p className="text-sm text-foreground">{profileData.activeSubscriptions}</p>
              </div>
            </div>
          )}
          {profileData.unreadReports !== undefined && (
            <div className="flex items-start gap-3">
              <Mail className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Непрочитанные отчеты</p>
                <p className="text-sm text-foreground">{profileData.unreadReports}</p>
              </div>
            </div>
          )}
        </div>
      );

    default:
      return null;
  }
};

/**
 * ProfileCard Component
 *
 * A reusable component for displaying user profiles across all dashboards.
 * Adapts content and display based on user role.
 */
export const ProfileCard: React.FC<ProfileCardProps> = ({
  userName,
  userEmail,
  userRole,
  avatarUrl,
  profileData,
  onEdit,
  className,
}) => {
  const roleConfig = getRoleConfig(userRole);
  const initials = useMemo(() => getInitials(userName), [userName]);

  return (
    <Card className={cn("w-full overflow-hidden transition-shadow hover:shadow-md", className)}>
      {/* Header with background gradient */}
      <div className="h-24 bg-gradient-to-r from-primary/10 to-primary/5" />

      {/* Main Content */}
      <CardHeader className="pt-0">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 -mt-16 relative z-10">
          {/* Avatar and basic info */}
          <div className="flex gap-4 items-start flex-1">
            <Avatar className="h-24 w-24 border-4 border-background">
              <AvatarImage src={avatarUrl} alt={userName} />
              <AvatarFallback className="text-lg font-semibold bg-primary text-primary-foreground">
                {initials}
              </AvatarFallback>
            </Avatar>

            <div className="pt-6 flex-1 min-w-0">
              <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 mb-2">
                <h2 className="text-xl sm:text-2xl font-bold leading-tight break-words">{userName}</h2>
                <Badge variant={roleConfig.variant} className="w-fit">
                  {roleConfig.label}
                </Badge>
              </div>

              <div className="flex items-center gap-2 text-muted-foreground truncate">
                <Mail className="h-4 w-4 flex-shrink-0" />
                <span className="text-sm truncate">{userEmail}</span>
              </div>
            </div>
          </div>

          {/* Edit button */}
          {onEdit && (
            <Button
              onClick={onEdit}
              variant="outline"
              size="sm"
              className="w-full sm:w-auto flex gap-2"
            >
              <Edit className="h-4 w-4" />
              <span className="hidden sm:inline">Редактировать</span>
              <span className="sm:hidden">Редакт.</span>
            </Button>
          )}
        </div>
      </CardHeader>

      {/* Role-specific information */}
      <CardContent className="pt-0">
        {renderRoleSpecificInfo(userRole, profileData)}
      </CardContent>
    </Card>
  );
};

export default ProfileCard;
