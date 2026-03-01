-- ============================================================
-- Supabase Setup for Violation Tracker Role-Based Auth
-- Run this in your Supabase SQL Editor (Dashboard > SQL Editor)
-- ============================================================
-- IMPORTANT: This assumes you already have a `students` table.
-- It creates: profiles, violations, helper functions, RLS policies.
-- ============================================================

-- Step 0: Clean up everything
DO $$ BEGIN
    EXECUTE 'DROP POLICY IF EXISTS "Students can view own violations" ON violations';
    EXECUTE 'DROP POLICY IF EXISTS "Teachers can view all violations" ON violations';
    EXECUTE 'DROP POLICY IF EXISTS "Admins full access violations" ON violations';
    EXECUTE 'DROP POLICY IF EXISTS "Teachers can insert violations" ON violations';
EXCEPTION WHEN OTHERS THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'DROP POLICY IF EXISTS "Users can read own profile" ON profiles';
    EXECUTE 'DROP POLICY IF EXISTS "Admins can read all profiles" ON profiles';
    EXECUTE 'DROP POLICY IF EXISTS "Admins can insert profiles" ON profiles';
    EXECUTE 'DROP POLICY IF EXISTS "Admins can update profiles" ON profiles';
    EXECUTE 'DROP POLICY IF EXISTS "Admins can delete profiles" ON profiles';
    EXECUTE 'DROP POLICY IF EXISTS "Users can insert own profile" ON profiles';
EXCEPTION WHEN OTHERS THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'DROP POLICY IF EXISTS "Students can read own student record" ON students';
    EXECUTE 'DROP POLICY IF EXISTS "Teachers can read all students" ON students';
    EXECUTE 'DROP POLICY IF EXISTS "Admins full access students" ON students';
EXCEPTION WHEN OTHERS THEN NULL; END $$;

DROP TABLE IF EXISTS violations CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;
DROP FUNCTION IF EXISTS public.get_my_role CASCADE;
DROP FUNCTION IF EXISTS public.is_admin CASCADE;
DROP FUNCTION IF EXISTS public.is_teacher CASCADE;
DROP FUNCTION IF EXISTS public.get_my_student_id CASCADE;
DROP FUNCTION IF EXISTS public.find_student_by_surname CASCADE;

-- ============================================================
-- Step 1: Create profiles table
-- ============================================================
CREATE TABLE profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('student', 'teacher', 'admin')) DEFAULT 'student',
    full_name TEXT NOT NULL DEFAULT '',
    student_id BIGINT REFERENCES students(id) ON DELETE SET NULL DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Step 2: Create violations table
-- ============================================================
CREATE TABLE violations (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT REFERENCES students(id) ON DELETE CASCADE,
    violation_type TEXT NOT NULL,
    description TEXT DEFAULT '',
    reported_by TEXT DEFAULT 'System',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Step 3: Enable Row Level Security
-- ============================================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE violations ENABLE ROW LEVEL SECURITY;
ALTER TABLE students ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- HELPER FUNCTIONS (must come AFTER tables are created)
-- SECURITY DEFINER = bypass RLS, fixes recursion
-- ============================================================

CREATE OR REPLACE FUNCTION public.get_my_role()
RETURNS TEXT AS $$
    SELECT role FROM public.profiles WHERE id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER STABLE;

CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN AS $$
    SELECT EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin');
$$ LANGUAGE sql SECURITY DEFINER STABLE;

CREATE OR REPLACE FUNCTION public.is_teacher()
RETURNS BOOLEAN AS $$
    SELECT EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'teacher');
$$ LANGUAGE sql SECURITY DEFINER STABLE;

CREATE OR REPLACE FUNCTION public.get_my_student_id()
RETURNS BIGINT AS $$
    SELECT student_id FROM public.profiles WHERE id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- ============================================================
-- STUDENT SURNAME LOOKUP (for login — callable without auth)
-- ============================================================

CREATE OR REPLACE FUNCTION public.find_student_by_name(p_name TEXT)
RETURNS TABLE(student_lrn TEXT, student_name TEXT) AS $$
    SELECT s.lrn, s.name
    FROM public.students s
    WHERE LOWER(s.name) LIKE '%' || LOWER(TRIM(p_name)) || '%'
    ORDER BY s.name
    LIMIT 10;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- ============================================================
-- PROFILES POLICIES (use helper functions to avoid recursion!)
-- ============================================================

CREATE POLICY "Users can read own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Admins can read all profiles"
    ON profiles FOR SELECT
    USING (public.is_admin());

CREATE POLICY "Admins can insert profiles"
    ON profiles FOR INSERT
    WITH CHECK (public.is_admin());

CREATE POLICY "Admins can update profiles"
    ON profiles FOR UPDATE
    USING (public.is_admin());

CREATE POLICY "Admins can delete profiles"
    ON profiles FOR DELETE
    USING (public.is_admin());

CREATE POLICY "Users can insert own profile"
    ON profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

-- ============================================================
-- VIOLATIONS POLICIES
-- ============================================================

CREATE POLICY "Students can view own violations"
    ON violations FOR SELECT
    USING (student_id = public.get_my_student_id());

CREATE POLICY "Teachers can view all violations"
    ON violations FOR SELECT
    USING (public.is_teacher());

CREATE POLICY "Admins full access violations"
    ON violations FOR ALL
    USING (public.is_admin());

CREATE POLICY "Teachers can insert violations"
    ON violations FOR INSERT
    WITH CHECK (public.is_teacher());

-- ============================================================
-- STUDENTS TABLE POLICIES
-- ============================================================

CREATE POLICY "Students can read own student record"
    ON students FOR SELECT
    USING (id = public.get_my_student_id());

CREATE POLICY "Teachers can read all students"
    ON students FOR SELECT
    USING (public.is_teacher());

CREATE POLICY "Admins full access students"
    ON students FOR ALL
    USING (public.is_admin());

CREATE POLICY "Teachers can insert students"
    ON students FOR INSERT
    WITH CHECK (public.is_teacher());

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX idx_violations_student ON violations(student_id);
CREATE INDEX idx_violations_type ON violations(violation_type);
CREATE INDEX idx_profiles_role ON profiles(role);
CREATE INDEX idx_profiles_student_id ON profiles(student_id);

-- ============================================================
-- TRIGGER: Auto-create profile on signup
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
    v_student_id BIGINT := NULL;
    v_lrn TEXT := NEW.raw_user_meta_data->>'lrn';
BEGIN
    IF v_lrn IS NOT NULL AND v_lrn != '' THEN
        SELECT id INTO v_student_id FROM public.students WHERE lrn = v_lrn;
    END IF;

    INSERT INTO public.profiles (id, role, full_name, student_id)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'role', 'student'),
        COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
        v_student_id
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- Auto-create profiles for any existing auth users that don't have one
-- This ensures your admin account gets a profile row
-- ============================================================
INSERT INTO profiles (id, role, full_name)
SELECT u.id,
       COALESCE(u.raw_user_meta_data->>'role', 'admin'),
       COALESCE(u.raw_user_meta_data->>'full_name', u.email)
FROM auth.users u
WHERE NOT EXISTS (SELECT 1 FROM profiles p WHERE p.id = u.id)
ON CONFLICT (id) DO NOTHING;
