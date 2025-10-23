import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { BookOpen, Mail } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { validateEmail, validatePassword, validateName, getErrorMessage } from "@/utils/validation";
import { ValidationMessage } from "@/components/ValidationMessage";

const Auth = () => {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [loginData, setLoginData] = useState({ email: "", password: "" });
  const [signupData, setSignupData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    role: "",
    name: "",
    phone: ""
  });

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    // Валидация email
    if (!validateEmail(loginData.email)) {
      toast.error("Пожалуйста, введите корректный email адрес");
      setIsLoading(false);
      return;
    }

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: loginData.email,
        password: loginData.password,
      });

      if (error) {
        console.error('Login error details:', error);
        toast.error(getErrorMessage(error));
        return;
      }

      if (data.user) {
        toast.success("Вход выполнен успешно!");
        
        // Получаем профиль пользователя для определения роли
        const { data: profile } = await supabase
          .from('profiles')
          .select('*')
          .eq('id', data.user.id)
          .single();

        // Получаем роли пользователя
        const { data: roles } = await supabase
          .from('user_roles')
          .select('role')
          .eq('user_id', data.user.id);

        const userRole = roles?.[0]?.role || 'student';
        
        // Переадресация в зависимости от роли
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
      }
    } catch (error) {
      toast.error("Произошла ошибка при входе");
      console.error('Login error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Валидация email
    if (!validateEmail(signupData.email)) {
      toast.error("Пожалуйста, введите корректный email адрес");
      return;
    }
    
    // Валидация имени
    const nameValidation = validateName(signupData.name);
    if (!nameValidation.isValid) {
      toast.error(nameValidation.message!);
      return;
    }
    
    // Валидация пароля
    const passwordValidation = validatePassword(signupData.password);
    if (!passwordValidation.isValid) {
      toast.error(passwordValidation.message!);
      return;
    }
    
    if (signupData.password !== signupData.confirmPassword) {
      toast.error("Пароли не совпадают");
      return;
    }

    if (!signupData.role) {
      toast.error("Пожалуйста, выберите роль");
      return;
    }

    setIsLoading(true);

    try {
      // Регистрация пользователя
      const { data, error } = await supabase.auth.signUp({
        email: signupData.email,
        password: signupData.password,
        options: {
          data: {
            full_name: signupData.name,
            role: signupData.role,
            phone: signupData.phone
          }
        }
      });

      if (error) {
        console.error('Signup error details:', error);
        toast.error(getErrorMessage(error));
        return;
      }

      if (data.user) {
        toast.success("Регистрация успешна! Проверьте email для подтверждения.");
        
        // Переключаемся на вкладку входа
        setIsLogin(true);
        setLoginData({ email: signupData.email, password: "" });
      }
    } catch (error) {
      toast.error("Произошла ошибка при регистрации");
      console.error('Signup error:', error);
    } finally {
      setIsLoading(false);
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
            <p className="text-muted-foreground">Войдите или создайте новый аккаунт</p>
          </div>

          <Tabs value={isLogin ? "login" : "signup"} onValueChange={(value) => setIsLogin(value === "login")} className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-8">
              <TabsTrigger value="login">Вход</TabsTrigger>
              <TabsTrigger value="signup">Регистрация</TabsTrigger>
            </TabsList>

            <TabsContent value="login">
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="login-email">Email</Label>
                  <Input
                    id="login-email"
                    type="email"
                    value={loginData.email}
                    onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                    placeholder="example@mail.ru"
                    required
                    pattern="[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
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

                <div className="relative my-6">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-card px-2 text-muted-foreground">Или войти через</span>
                  </div>
                </div>

                <div className="grid gap-3">
                  <Button type="button" variant="outline" className="w-full">
                    <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                      <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                      <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                      <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                      <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    Google
                  </Button>
                  
                  <Button type="button" variant="outline" className="w-full">
                    <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 2C6.48 2 2 6.48 2 12c0 4.42 2.87 8.17 6.84 9.49.5.09.66-.22.66-.48l-.01-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.15-1.11-1.46-1.11-1.46-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.89 1.52 2.34 1.08 2.91.83.09-.65.35-1.08.63-1.33-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02.8-.22 1.65-.33 2.5-.33.85 0 1.7.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85l-.01 2.75c0 .27.16.58.67.48C19.14 20.16 22 16.42 22 12c0-5.52-4.48-10-10-10z"/>
                    </svg>
                    Telegram
                  </Button>
                </div>
              </form>
            </TabsContent>

            <TabsContent value="signup">
              <form onSubmit={handleSignup} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="signup-role">Роль *</Label>
                  <Select value={signupData.role} onValueChange={(value) => setSignupData({ ...signupData, role: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите роль" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="student">Ученик</SelectItem>
                      <SelectItem value="parent">Родитель</SelectItem>
                      <SelectItem value="teacher">Преподаватель</SelectItem>
                      <SelectItem value="tutor">Тьютор</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="signup-name">Имя *</Label>
                  <Input
                    id="signup-name"
                    value={signupData.name}
                    onChange={(e) => setSignupData({ ...signupData, name: e.target.value })}
                    placeholder="Иван Иванов"
                    required
                  />
                  <ValidationMessage type="name" value={signupData.name} />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="signup-email">Email *</Label>
                  <Input
                    id="signup-email"
                    type="email"
                    value={signupData.email}
                    onChange={(e) => setSignupData({ ...signupData, email: e.target.value })}
                    placeholder="example@mail.ru"
                    required
                    pattern="[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
                  />
                  <ValidationMessage type="email" value={signupData.email} />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="signup-phone">Телефон *</Label>
                  <Input
                    id="signup-phone"
                    type="tel"
                    value={signupData.phone}
                    onChange={(e) => setSignupData({ ...signupData, phone: e.target.value })}
                    placeholder="+7 (999) 123-45-67"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="signup-password">Пароль *</Label>
                  <Input
                    id="signup-password"
                    type="password"
                    value={signupData.password}
                    onChange={(e) => setSignupData({ ...signupData, password: e.target.value })}
                    placeholder="••••••••"
                    required
                  />
                  <ValidationMessage type="password" value={signupData.password} />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="signup-confirm">Подтвердите пароль *</Label>
                  <Input
                    id="signup-confirm"
                    type="password"
                    value={signupData.confirmPassword}
                    onChange={(e) => setSignupData({ ...signupData, confirmPassword: e.target.value })}
                    placeholder="••••••••"
                    required
                  />
                </div>

                <Button type="submit" className="w-full gradient-primary shadow-glow" disabled={isLoading}>
                  {isLoading ? "Регистрация..." : "Зарегистрироваться"}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </Card>
      </div>
    </div>
  );
};

export default Auth;
