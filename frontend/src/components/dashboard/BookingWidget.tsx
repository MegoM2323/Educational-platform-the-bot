import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { Calendar, Clock, BookOpen, ArrowRight, RefreshCw, ExternalLink } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useStudentSchedule } from "@/hooks/useStudentSchedule";
import { useCountdown } from "@/hooks/useCountdown";
import { format } from "date-fns";
import { ru } from "date-fns/locale";

const NextLessonCountdown = ({ datetime_start }: { datetime_start: string }) => {
  const targetDate = new Date(datetime_start);
  const { timeLeft, isUrgent, isStartingNow } = useCountdown(targetDate);

  return (
    <div className={`text-lg font-bold ${isUrgent ? 'text-destructive' : isStartingNow ? 'text-green-600' : 'text-foreground'}`}>
      {timeLeft}
    </div>
  );
};

export const BookingWidget = () => {
  const navigate = useNavigate();
  const { upcomingLessons, isLoading } = useStudentSchedule();

  const nextLessons = upcomingLessons.slice(0, 3);
  const nextLesson = nextLessons[0];

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64 mt-2" />
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
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-primary" />
              Мои занятия
            </CardTitle>
            <CardDescription>Расписание уроков</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Next Lesson */}
        {nextLesson ? (
          <>
            <div className="gradient-primary p-4 rounded-lg text-primary-foreground">
              <div className="space-y-3">
                <div>
                  <h4 className="font-semibold mb-1">Следующий урок</h4>
                  <NextLessonCountdown datetime_start={nextLesson.datetime_start} />
                </div>

                <div className="flex items-start gap-3">
                  <Avatar className="w-10 h-10">
                    <AvatarFallback className="bg-primary-foreground/20 text-primary-foreground text-xs font-bold">
                      {nextLesson.teacher_name
                        .split(' ')
                        .map(n => n[0])
                        .join('')
                        .toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm">{nextLesson.teacher_name}</div>
                    <div className="text-xs text-primary-foreground/80">{nextLesson.subject_name}</div>
                    <div className="flex items-center gap-2 text-xs text-primary-foreground/80 mt-1">
                      <Calendar className="w-3 h-3" />
                      {format(new Date(nextLesson.date), 'd MMMM', { locale: ru })}
                      <Clock className="w-3 h-3 ml-1" />
                      {nextLesson.start_time.slice(0, 5)} - {nextLesson.end_time.slice(0, 5)}
                    </div>
                  </div>
                </div>

                {nextLesson.telemost_link && (
                  <Button
                    asChild
                    variant="secondary"
                    className="w-full text-sm"
                  >
                    <a href={nextLesson.telemost_link} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="w-4 h-4 mr-2" />
                      Присоединиться к уроку
                    </a>
                  </Button>
                )}
              </div>
            </div>

            {/* Upcoming lessons list */}
            {nextLessons.length > 1 && (
              <div className="space-y-2">
                <h4 className="font-semibold text-sm text-foreground">Предстоящие занятия</h4>
                <div className="space-y-2">
                  {nextLessons.slice(1).map((lesson) => (
                    <div
                      key={lesson.id}
                      className="p-3 bg-muted rounded-lg hover:bg-muted/80 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <Avatar className="w-8 h-8 flex-shrink-0">
                          <AvatarFallback className="text-xs text-muted-foreground">
                            {lesson.teacher_name
                              .split(' ')
                              .map(n => n[0])
                              .join('')
                              .toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm truncate">{lesson.teacher_name}</div>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                            <span>{format(new Date(lesson.date), 'd MMM', { locale: ru })}</span>
                            <span>•</span>
                            <span>{lesson.start_time.slice(0, 5)}</span>
                            <span>•</span>
                            <span>{lesson.subject_name}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Calendar className="w-10 h-10 mx-auto mb-2 opacity-50" />
            <p className="text-sm font-medium">Нет предстоящих занятий</p>
            <p className="text-xs mt-1 text-muted-foreground/80">Обратитесь к преподавателю для планирования уроков</p>
          </div>
        )}

        {/* View All Button */}
        <Button
          variant="outline"
          className="w-full"
          onClick={() => navigate('/dashboard/student/schedule')}
        >
          Посмотреть расписание
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </CardContent>
    </Card>
  );
};
