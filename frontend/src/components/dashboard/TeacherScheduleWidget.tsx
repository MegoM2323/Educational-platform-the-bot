import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Calendar, Clock, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTeacherLessons } from "@/hooks/useTeacherLessons";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import { useMemo } from "react";
import { Lesson } from "@/types/scheduling";

export const TeacherScheduleWidget = () => {
  const navigate = useNavigate();
  const { lessons, isLoading } = useTeacherLessons();

  const upcomingLessons = useMemo(() => {
    const now = new Date();
    return lessons
      .filter((lesson: Lesson) => {
        const lessonDate = new Date(`${lesson.date}T${lesson.start_time}`);
        return lessonDate > now && (lesson.status === 'confirmed' || lesson.status === 'pending');
      })
      .sort((a: Lesson, b: Lesson) =>
        new Date(`${a.date}T${a.start_time}`).getTime() -
        new Date(`${b.date}T${b.start_time}`).getTime()
      )
      .slice(0, 3);
  }, [lessons]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-primary" />
          Следующие занятия
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {upcomingLessons.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Calendar className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Нет запланированных занятий</p>
          </div>
        ) : (
          upcomingLessons.map((lesson: Lesson, idx: number) => (
            <div key={lesson.id} className={`border-b pb-4 last:border-0 last:pb-0 ${idx > 0 ? 'pt-4' : ''}`}>
              <div className="flex justify-between items-start gap-4">
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm">{lesson.student_name}</p>
                  <p className="text-sm text-muted-foreground">{lesson.subject_name}</p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mt-2">
                    <Calendar className="w-3 h-3" />
                    <span>{format(new Date(`${lesson.date}T${lesson.start_time}`), 'd MMM yyyy', { locale: ru })}</span>
                    <span>•</span>
                    <Clock className="w-3 h-3" />
                    <span>{lesson.start_time.slice(0, 5)}</span>
                  </div>
                </div>
                {lesson.telemost_link && (
                  <Button type="button" size="sm" variant="outline" asChild className="whitespace-nowrap">
                    <a href={lesson.telemost_link} target="_blank" rel="noopener noreferrer">
                      Присоединиться
                    </a>
                  </Button>
                )}
              </div>
            </div>
          ))
        )}
      </CardContent>
      <div className="border-t px-6 py-4">
        <Button type="button" variant="outline" asChild className="w-full">
          <a href="/dashboard/teacher/schedule" className="flex items-center justify-center">
            Все занятия
            <ArrowRight className="w-4 h-4 ml-2" />
          </a>
        </Button>
      </div>
    </Card>
  );
};
