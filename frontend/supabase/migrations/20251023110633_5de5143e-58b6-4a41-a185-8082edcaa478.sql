-- Create enum for user roles
CREATE TYPE public.app_role AS ENUM ('student', 'parent', 'teacher', 'tutor');

-- Create profiles table
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT NOT NULL,
  phone TEXT,
  avatar_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Create user_roles table (CRITICAL: separate table for security)
CREATE TABLE public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  role app_role NOT NULL,
  UNIQUE(user_id, role)
);

ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

-- Create security definer function to check roles
CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role app_role)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.user_roles
    WHERE user_id = _user_id AND role = _role
  )
$$;

-- Create students table
CREATE TABLE public.students (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
  grade INTEGER NOT NULL,
  educational_goal TEXT NOT NULL,
  progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;

-- Create parent_student relationship
CREATE TABLE public.parent_students (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  student_id UUID REFERENCES public.students(id) ON DELETE CASCADE NOT NULL,
  UNIQUE(parent_id, student_id)
);

ALTER TABLE public.parent_students ENABLE ROW LEVEL SECURITY;

-- Create tutor_students relationship
CREATE TABLE public.tutor_students (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tutor_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  student_id UUID REFERENCES public.students(id) ON DELETE CASCADE NOT NULL,
  UNIQUE(tutor_id, student_id)
);

ALTER TABLE public.tutor_students ENABLE ROW LEVEL SECURITY;

-- Create materials table
CREATE TABLE public.materials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  teacher_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  content TEXT NOT NULL,
  subject TEXT NOT NULL,
  file_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.materials ENABLE ROW LEVEL SECURITY;

-- Create student_materials assignment table
CREATE TABLE public.student_materials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  material_id UUID REFERENCES public.materials(id) ON DELETE CASCADE NOT NULL,
  student_id UUID REFERENCES public.students(id) ON DELETE CASCADE NOT NULL,
  assigned_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(material_id, student_id)
);

ALTER TABLE public.student_materials ENABLE ROW LEVEL SECURITY;

-- Create homework table
CREATE TABLE public.homework (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  material_id UUID REFERENCES public.materials(id) ON DELETE CASCADE NOT NULL,
  student_id UUID REFERENCES public.students(id) ON DELETE CASCADE NOT NULL,
  submission TEXT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'submitted', 'checked', 'approved')),
  grade INTEGER CHECK (grade >= 0 AND grade <= 100),
  teacher_comment TEXT,
  submitted_at TIMESTAMPTZ,
  checked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.homework ENABLE ROW LEVEL SECURITY;

-- Create reports table
CREATE TABLE public.reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  author_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  student_id UUID REFERENCES public.students(id) ON DELETE CASCADE NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  subject TEXT,
  report_type TEXT NOT NULL CHECK (report_type IN ('teacher', 'tutor', 'final')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;

-- Create messages table for chat
CREATE TABLE public.messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sender_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  recipient_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  content TEXT NOT NULL,
  read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- Create payments table
CREATE TABLE public.payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  student_id UUID REFERENCES public.students(id) ON DELETE SET NULL,
  amount DECIMAL(10,2) NOT NULL,
  currency TEXT DEFAULT 'USD',
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
  payment_method TEXT,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

-- RLS Policies for profiles
CREATE POLICY "Users can view own profile"
  ON public.profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON public.profiles FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON public.profiles FOR INSERT
  WITH CHECK (auth.uid() = id);

-- RLS Policies for user_roles
CREATE POLICY "Users can view own roles"
  ON public.user_roles FOR SELECT
  USING (auth.uid() = user_id);

-- RLS Policies for students
CREATE POLICY "Students can view own data"
  ON public.students FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Teachers can view all students"
  ON public.students FOR SELECT
  USING (public.has_role(auth.uid(), 'teacher'));

CREATE POLICY "Tutors can view assigned students"
  ON public.students FOR SELECT
  USING (
    public.has_role(auth.uid(), 'tutor') AND
    id IN (SELECT student_id FROM public.tutor_students WHERE tutor_id = auth.uid())
  );

CREATE POLICY "Parents can view their children"
  ON public.students FOR SELECT
  USING (
    public.has_role(auth.uid(), 'parent') AND
    id IN (SELECT student_id FROM public.parent_students WHERE parent_id = auth.uid())
  );

-- RLS Policies for materials
CREATE POLICY "Students can view assigned materials"
  ON public.materials FOR SELECT
  USING (
    public.has_role(auth.uid(), 'student') AND
    id IN (
      SELECT material_id FROM public.student_materials sm
      JOIN public.students s ON s.id = sm.student_id
      WHERE s.user_id = auth.uid()
    )
  );

CREATE POLICY "Teachers can manage own materials"
  ON public.materials FOR ALL
  USING (auth.uid() = teacher_id);

-- RLS Policies for homework
CREATE POLICY "Students can view own homework"
  ON public.homework FOR SELECT
  USING (
    student_id IN (SELECT id FROM public.students WHERE user_id = auth.uid())
  );

CREATE POLICY "Students can update own homework"
  ON public.homework FOR UPDATE
  USING (
    student_id IN (SELECT id FROM public.students WHERE user_id = auth.uid())
  );

CREATE POLICY "Teachers can view and check homework"
  ON public.homework FOR ALL
  USING (
    public.has_role(auth.uid(), 'teacher') AND
    material_id IN (SELECT id FROM public.materials WHERE teacher_id = auth.uid())
  );

-- RLS Policies for reports
CREATE POLICY "Students can view own reports"
  ON public.reports FOR SELECT
  USING (
    student_id IN (SELECT id FROM public.students WHERE user_id = auth.uid())
  );

CREATE POLICY "Parents can view children reports"
  ON public.reports FOR SELECT
  USING (
    public.has_role(auth.uid(), 'parent') AND
    student_id IN (SELECT student_id FROM public.parent_students WHERE parent_id = auth.uid())
  );

CREATE POLICY "Teachers can manage own reports"
  ON public.reports FOR ALL
  USING (
    public.has_role(auth.uid(), 'teacher') AND
    auth.uid() = author_id
  );

CREATE POLICY "Tutors can manage reports for assigned students"
  ON public.reports FOR ALL
  USING (
    public.has_role(auth.uid(), 'tutor') AND
    student_id IN (SELECT student_id FROM public.tutor_students WHERE tutor_id = auth.uid())
  );

-- RLS Policies for messages
CREATE POLICY "Users can view own messages"
  ON public.messages FOR SELECT
  USING (auth.uid() = sender_id OR auth.uid() = recipient_id);

CREATE POLICY "Users can send messages"
  ON public.messages FOR INSERT
  WITH CHECK (auth.uid() = sender_id);

CREATE POLICY "Users can update own received messages"
  ON public.messages FOR UPDATE
  USING (auth.uid() = recipient_id);

-- RLS Policies for payments
CREATE POLICY "Users can view own payments"
  ON public.payments FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own payments"
  ON public.payments FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Create function to handle new user
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name)
  VALUES (
    new.id,
    COALESCE(new.raw_user_meta_data->>'full_name', new.email)
  );
  RETURN new;
END;
$$;

-- Trigger for new user creation
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

-- Add updated_at triggers
CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON public.materials
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON public.reports
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON public.payments
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();