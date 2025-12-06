import { useLocation, useNavigate } from "react-router-dom";
import { logger } from '@/utils/logger';
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/contexts/AuthContext";
import { Home, ArrowLeft, LayoutDashboard } from "lucide-react";

const NotFound = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    logger.error("404 Error: User attempted to access non-existent route:", location.pathname);
  }, [location.pathname]);

  const handleBackClick = () => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate('/');
    }
  };

  const getDashboardRoute = () => {
    if (!user?.role) return '/';
    return `/dashboard/${user.role}`;
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background via-muted/20 to-background p-4">
      <Card className="max-w-md w-full p-8 shadow-lg">
        <div className="text-center space-y-6">
          {/* 404 Badge */}
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-destructive/10 text-destructive">
            <span className="text-4xl font-bold">404</span>
          </div>

          {/* Title */}
          <div className="space-y-2">
            <h1 className="text-3xl font-bold">Упс! Страница не найдена</h1>
            <p className="text-muted-foreground">
              Похоже, страница, которую вы ищете, не существует или была перемещена
            </p>
          </div>

          {/* Navigation Buttons */}
          <div className="flex flex-col gap-3 pt-4">
            <Button type="button"
              onClick={handleBackClick}
              variant="outline"
              className="w-full gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Вернуться назад
            </Button>

            <Button type="button"
              onClick={() => navigate('/')}
              variant="default"
              className="w-full gap-2"
            >
              <Home className="w-4 h-4" />
              На главную
            </Button>

            {user && (
              <Button type="button"
                onClick={() => navigate(getDashboardRoute())}
                className="w-full gap-2 gradient-primary shadow-glow"
              >
                <LayoutDashboard className="w-4 h-4" />
                В мой кабинет
              </Button>
            )}
          </div>

          {/* Additional Info */}
          <p className="text-sm text-muted-foreground pt-4">
            Путь: <code className="text-xs bg-muted px-2 py-1 rounded">{location.pathname}</code>
          </p>
        </div>
      </Card>
    </div>
  );
};

export default NotFound;
