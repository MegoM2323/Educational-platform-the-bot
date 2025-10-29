import { useState, memo } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { BookOpen } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { authService } from "@/services/authService";
import { validateEmail } from "@/utils/validation";

const Auth = memo(() => {
  const navigate = useNavigate();
  const { login, isLoading } = useAuth();
  const [loginData, setLoginData] = useState({ emailOrUsername: "", password: "" });
  const [loginType, setLoginType] = useState<"email" | "username">("email");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    // Валидация email только если выбран тип "email"
    if (loginType === "email") {
      if (!validateEmail(loginData.emailOrUsername)) {
        toast.error("Пожалуйста, введите корректный email адрес");
        return;
      }
    } else {
      if (!loginData.emailOrUsername.trim()) {
        toast.error("Пожалуйста, введите имя пользователя");
        return;
      }
    }

    try {
      // Вход через AuthContext (по умолчанию ВСЕГДА обращаемся к backend)
      // Dev bypass возможен только при явном флаге VITE_AUTH_DEV_BYPASS === 'true'
      if (import.meta.env.VITE_AUTH_DEV_BYPASS === 'true') {
        const email = loginData.emailOrUsername.trim().toLowerCase();
        const role = email.includes('parent') ? 'parent' : email.includes('teacher') ? 'teacher' : email.includes('tutor') ? 'tutor' : 'student';
        const mockUser = {
          id: role === 'parent' ? 4 : role === 'teacher' ? 3 : role === 'tutor' ? 2 : 1,
          email: loginData.emailOrUsername,
          first_name: 'Test',
          last_name: 'User',
          role,
          role_display: role.charAt(0).toUpperCase() + role.slice(1),
          phone: '+79990000000',
          is_verified: true,
          date_joined: new Date().toISOString(),
          full_name: 'Test User'
        } as any;
        localStorage.setItem('authToken', 'dev-token');
        localStorage.setItem('userData', JSON.stringify(mockUser));
        await new Promise(r => setTimeout(r, 50));
        switch (role) {
          case 'parent':
            navigate('/dashboard/parent');
            break;
          case 'teacher':
            navigate('/dashboard/teacher');
            break;
          case 'tutor':
            navigate('/dashboard/tutor');
            break;
          default:
            navigate('/dashboard/student');
        }
        toast.success('Вход выполнен (dev bypass)');
        return;
      }

      // Стандартный путь — реальный запрос к backend
      const loginCredentials = loginType === "email" 
        ? { email: loginData.emailOrUsername, password: loginData.password }
        : { username: loginData.emailOrUsername, password: loginData.password };
      
      const result = await login(loginCredentials);

      toast.success("Вход выполнен успешно!");
      
      // Переадресация в зависимости от роли
      const userRole = result.user.role;
      // Небольшая задержка, чтобы контекст успел зафиксировать пользователя (устойчивость E2E)
      await new Promise(r => setTimeout(r, 50));
      switch (userRole) {
        case 'student':
          navigate('/dashboard/student');
          break;
        case 'teacher':
          navigate('/dashboard/teacher');
          break;
        case 'tutor':
          navigate('/dashboard/tutor');
          break;
        case 'parent':
          navigate('/dashboard/parent');
          break;
        default:
          navigate('/dashboard/student');
      }
    } catch (error) {
      console.error('Login error:', error);
      toast.error("Произошла ошибка при входе");
    }
  };


  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-background via-muted/20 to-background">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <Link to="/" className="flex items-center gap-2 w-fit">
            <div className="w-10 h-10 gradient-primary rounded-lg flex items-center justify-center">
              <BookOpen className="w-6 h-6 text-primary-foreground" />
            </div>
            <span className="text-2xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              THE BOT
            </span>
          </Link>
        </div>
      </header>

      {/* Auth Form */}
      <div className="flex-1 flex items-center justify-center p-4">
        <Card className="w-full max-w-md p-8 shadow-lg">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2">Добро пожаловать!</h1>
            <p className="text-muted-foreground">Войдите в свой аккаунт</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
                {/* Тoggle для выбора типа входа */}
                <div className="flex gap-2 mb-4">
                  <Button
                    type="button"
                    variant={loginType === "email" ? "default" : "outline"}
                    onClick={() => setLoginType("email")}
                    className="flex-1"
                  >
                    Email
                  </Button>
                  <Button
                    type="button"
                    variant={loginType === "username" ? "default" : "outline"}
                    onClick={() => setLoginType("username")}
                    className="flex-1"
                  >
                    Логин
                  </Button>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="login-identifier">
                    {loginType === "email" ? "Email" : "Имя пользователя"}
                  </Label>
                  <Input
                    id="login-identifier"
                    type={loginType === "email" ? "email" : "text"}
                    value={loginData.emailOrUsername}
                    onChange={(e) => setLoginData({ ...loginData, emailOrUsername: e.target.value })}
                    placeholder={loginType === "email" ? "example@mail.ru" : "mylogin"}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="login-password">Пароль</Label>
                  <Input
                    id="login-password"
                    type="password"
                    value={loginData.password}
                    onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                    placeholder="••••••••"
                    required
                  />
                </div>

                <Button type="submit" className="w-full gradient-primary shadow-glow" disabled={isLoading}>
                  {isLoading ? "Вход..." : "Войти"}
                </Button>

                {/* Соц. входы отключены */}
          </form>
        </Card>
      </div>
    </div>
  );
});

Auth.displayName = 'Auth';

export default Auth;
