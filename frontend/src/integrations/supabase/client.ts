// Supabase клиент для аутентификации
import { createClient, SupabaseClient, User as SupabaseUser, AuthError } from '@supabase/supabase-js';
import { User } from '@/integrations/api/unifiedClient';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

export interface SupabaseAuthResult {
  user: User | null;
  session: any | null;
  error: AuthError | null;
}

export interface SupabaseAuthService {
  signInWithEmail(email: string, password: string): Promise<SupabaseAuthResult>;
  signUpWithEmail(email: string, password: string, userData?: any): Promise<SupabaseAuthResult>;
  signOut(): Promise<{ error: AuthError | null }>;
  getCurrentUser(): User | null;
  onAuthStateChange(callback: (user: User | null) => void): () => void;
}

class SupabaseAuthServiceImpl implements SupabaseAuthService {
  private supabase: SupabaseClient | null = null;
  private authStateCallbacks: ((user: User | null) => void)[] = [];

  constructor() {
    this.initializeSupabase();
  }

  private initializeSupabase(): void {
    if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
      console.warn('Supabase credentials не найдены. Supabase аутентификация недоступна.');
      return;
    }

    try {
      this.supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
      
      // Подписываемся на изменения состояния аутентификации
      this.supabase.auth.onAuthStateChange((event, session) => {
        const user = session?.user ? this.transformSupabaseUser(session.user) : null;
        this.notifyAuthStateChange(user);
      });
    } catch (error) {
      console.error('Ошибка инициализации Supabase:', error);
    }
  }

  private transformSupabaseUser(supabaseUser: SupabaseUser): User {
    return {
      id: parseInt(supabaseUser.id) || 0,
      email: supabaseUser.email || '',
      first_name: supabaseUser.user_metadata?.first_name || '',
      last_name: supabaseUser.user_metadata?.last_name || '',
      role: supabaseUser.user_metadata?.role || 'student',
      role_display: supabaseUser.user_metadata?.role_display || 'Студент',
      phone: supabaseUser.user_metadata?.phone || '',
      avatar: supabaseUser.user_metadata?.avatar_url || supabaseUser.user_metadata?.avatar,
      is_verified: supabaseUser.email_confirmed_at ? true : false,
      date_joined: supabaseUser.created_at || new Date().toISOString(),
      full_name: `${supabaseUser.user_metadata?.first_name || ''} ${supabaseUser.user_metadata?.last_name || ''}`.trim(),
    };
  }

  private notifyAuthStateChange(user: User | null): void {
    this.authStateCallbacks.forEach(callback => {
      try {
        callback(user);
      } catch (error) {
        console.error('Ошибка в callback Supabase аутентификации:', error);
      }
    });
  }

  public async signInWithEmail(email: string, password: string): Promise<SupabaseAuthResult> {
    if (!this.supabase) {
      return {
        user: null,
        session: null,
        error: { message: 'Supabase не инициализирован', name: 'AuthError' } as AuthError,
      };
    }

    try {
      const { data, error } = await this.supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        return {
          user: null,
          session: null,
          error,
        };
      }

      const user = data.user ? this.transformSupabaseUser(data.user) : null;
      
      return {
        user,
        session: data.session,
        error: null,
      };
    } catch (error) {
      return {
        user: null,
        session: null,
        error: { message: 'Неожиданная ошибка аутентификации', name: 'AuthError' } as AuthError,
      };
    }
  }

  public async signUpWithEmail(email: string, password: string, userData?: any): Promise<SupabaseAuthResult> {
    if (!this.supabase) {
      return {
        user: null,
        session: null,
        error: { message: 'Supabase не инициализирован', name: 'AuthError' } as AuthError,
      };
    }

    try {
      const { data, error } = await this.supabase.auth.signUp({
        email,
        password,
        options: {
          data: userData || {},
        },
      });

      if (error) {
        return {
          user: null,
          session: null,
          error,
        };
      }

      const user = data.user ? this.transformSupabaseUser(data.user) : null;
      
      return {
        user,
        session: data.session,
        error: null,
      };
    } catch (error) {
      return {
        user: null,
        session: null,
        error: { message: 'Неожиданная ошибка регистрации', name: 'AuthError' } as AuthError,
      };
    }
  }

  public async signOut(): Promise<{ error: AuthError | null }> {
    if (!this.supabase) {
      return { error: { message: 'Supabase не инициализирован', name: 'AuthError' } as AuthError };
    }

    try {
      const { error } = await this.supabase.auth.signOut();
      return { error };
    } catch (error) {
      return { error: { message: 'Неожиданная ошибка выхода', name: 'AuthError' } as AuthError };
    }
  }

  public getCurrentUser(): User | null {
    if (!this.supabase) {
      return null;
    }

    try {
      const session = this.supabase.auth.getSession();
      if (session.data?.session?.user) {
        return this.transformSupabaseUser(session.data.session.user);
      }
      return null;
    } catch (error) {
      console.error('Ошибка получения текущего пользователя:', error);
      return null;
    }
  }

  public onAuthStateChange(callback: (user: User | null) => void): () => void {
    this.authStateCallbacks.push(callback);
    
    // Возвращаем функцию для отписки
    return () => {
      const index = this.authStateCallbacks.indexOf(callback);
      if (index > -1) {
        this.authStateCallbacks.splice(index, 1);
      }
    };
  }

  public isAvailable(): boolean {
    return !!this.supabase;
  }

  public getSupabaseClient(): SupabaseClient | null {
    return this.supabase;
  }
}

// Создаем и экспортируем singleton instance
export const supabaseAuthService = new SupabaseAuthServiceImpl();

// Экспортируем класс для тестирования
export { SupabaseAuthServiceImpl };
