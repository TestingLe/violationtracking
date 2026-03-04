/**
 * Supabase Configuration
 * Central config file — all pages import from here.
 */

const SUPABASE_URL = 'https://xqakwpuecrbzpvskiafd.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhxYWt3cHVlY3JienB2c2tpYWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEyMTg4MjEsImV4cCI6MjA4Njc5NDgyMX0.kaLcRdUHwgpteKfiUr7PD3h9f7yn2xAF9d2xMKck3q8';

let _supabaseClient = null;

function getSupabaseClient() {
    if (!_supabaseClient) {
        _supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
    }
    return _supabaseClient;
}

/**
 * Get current session user's profile (role, full_name, student_id)
 * If the user is a student, also fetches their student record (name, lrn, grade, section, sex)
 */
async function getUserProfile() {
    const sb = getSupabaseClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) return null;

    const { data, error } = await sb
        .from('profiles')
        .select('id, role, full_name, student_id, students(id, name, lrn, sex, grade, section, phone, email)')
        .eq('id', session.user.id)
        .single();

    if (error) {
        console.error('Profile fetch error:', error);
        return null;
    }

    // Flatten student info if available
    const studentInfo = data.students || null;
    return {
        id: data.id,
        role: data.role,
        full_name: data.full_name || (studentInfo ? studentInfo.name : ''),
        student_id: data.student_id,
        student: studentInfo,
        email: session.user.email
    };
}

/**
 * Redirect helper based on role
 */
function redirectToDashboard(role) {
    switch (role) {
        case 'student':
            window.location.href = 'student_dashboard.html';
            break;
        case 'teacher':
            window.location.href = 'teacher_dashboard.html';
            break;
        case 'admin':
            window.location.href = 'admin.html';
            break;
        default:
            window.location.href = 'index.html';
    }
}

/**
 * Logout and redirect to login
 */
async function logout() {
    const sb = getSupabaseClient();
    await sb.auth.signOut();
    window.location.href = 'index.html';
}
