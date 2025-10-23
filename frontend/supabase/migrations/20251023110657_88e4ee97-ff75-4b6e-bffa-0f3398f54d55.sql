-- Fix search_path for handle_new_user function
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

-- Add RLS policies for parent_students
CREATE POLICY "Parents can view their children relationships"
  ON public.parent_students FOR SELECT
  USING (auth.uid() = parent_id);

CREATE POLICY "Parents can manage their children relationships"
  ON public.parent_students FOR ALL
  USING (auth.uid() = parent_id);

-- Add RLS policies for tutor_students
CREATE POLICY "Tutors can view their students relationships"
  ON public.tutor_students FOR SELECT
  USING (auth.uid() = tutor_id);

CREATE POLICY "Tutors can manage their students relationships"
  ON public.tutor_students FOR ALL
  USING (auth.uid() = tutor_id);

-- Add RLS policies for student_materials
CREATE POLICY "Students can view their assigned materials"
  ON public.student_materials FOR SELECT
  USING (
    student_id IN (SELECT id FROM public.students WHERE user_id = auth.uid())
  );

CREATE POLICY "Teachers can manage material assignments"
  ON public.student_materials FOR ALL
  USING (
    public.has_role(auth.uid(), 'teacher') AND
    material_id IN (SELECT id FROM public.materials WHERE teacher_id = auth.uid())
  );