import { Info } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface PrivateFieldTooltipProps {
  role: 'student' | 'teacher' | 'tutor' | 'parent';
  field: string;
}

/**
 * Компонент для визуального обозначения приватных полей в формах
 *
 * Приватные поля:
 * - StudentProfile: goal, tutor, parent (видят teacher/tutor/admin, НЕ видит студент)
 * - TeacherProfile: bio, experience_years (видит только admin, НЕ видит преподаватель)
 * - TutorProfile: bio, experience_years (видит только admin, НЕ видит тьютор)
 */
export const PrivateFieldTooltip = ({ role, field }: PrivateFieldTooltipProps) => {
  const getTooltipText = () => {
    if (role === 'student') {
      if (['goal', 'tutor', 'parent', 'tutor_id', 'parent_id'].includes(field)) {
        return 'Студент не видит это поле. Видят: преподаватели, тьюторы, администраторы';
      }
    } else if (role === 'teacher' || role === 'tutor') {
      if (['bio', 'experience_years'].includes(field)) {
        return `${role === 'teacher' ? 'Преподаватель' : 'Тьютор'} не видит это поле. Видят: только администраторы`;
      }
    }
    return null;
  };

  const tooltipText = getTooltipText();

  if (!tooltipText) return null;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Info className="h-4 w-4 text-muted-foreground cursor-help" />
        </TooltipTrigger>
        <TooltipContent side="right" className="max-w-xs">
          <p>{tooltipText}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};
