/**
 * Supabase Auth Guard — Role-Based
 * Include this script on any page that requires authentication.
 * Usage: Add data-allowed-roles="admin,teacher" attribute to <body> to restrict access.
 */

// Hide page until auth check completes (prevent flash of content)
document.body.style.visibility = 'hidden';

(async function authGuard() {
    const sb = getSupabaseClient();
    const { data: { session } } = await sb.auth.getSession();

    if (!session) {
        window.location.href = 'index.html';
        return;
    }

    // Get user profile with role
    const profile = await getUserProfile();
    if (!profile) {
        await sb.auth.signOut();
        window.location.href = 'index.html';
        return;
    }

    // Check if page has role restrictions
    const allowedRolesAttr = document.body.getAttribute('data-allowed-roles');
    if (allowedRolesAttr) {
        const allowedRoles = allowedRolesAttr.split(',').map(r => r.trim().toLowerCase());
        if (!allowedRoles.includes(profile.role)) {
            // User doesn't have the right role — redirect to their correct dashboard
            redirectToDashboard(profile.role);
            return;
        }
    }

    // User is authenticated and authorized — show the page
    document.body.style.visibility = 'visible';

    // Store profile globally for page scripts to use
    window.__userProfile = profile;

    // Dispatch custom event so page scripts can initialize
    window.dispatchEvent(new CustomEvent('auth-ready', { detail: profile }));

    // Add user info + logout button to navigation
    addUserNavInfo(profile);
})();

function addUserNavInfo(profile) {
    const nav = document.querySelector('.top-nav, .top-header, nav, header');
    if (!nav) return;
    if (document.getElementById('authUserSection')) return;

    const roleBadgeColors = {
        admin: { bg: 'rgba(255,68,102,0.15)', border: 'rgba(255,68,102,0.3)', color: '#ff4466' },
        teacher: { bg: 'rgba(0,136,255,0.15)', border: 'rgba(0,136,255,0.3)', color: '#0088ff' },
        student: { bg: 'rgba(0,255,136,0.15)', border: 'rgba(0,255,136,0.3)', color: '#00ff88' }
    };
    const badge = roleBadgeColors[profile.role] || roleBadgeColors.student;

    const section = document.createElement('div');
    section.id = 'authUserSection';
    section.style.cssText = 'display:flex;align-items:center;gap:10px;position:absolute;top:16px;right:20px;z-index:100;';
    section.innerHTML = `
        <span style="
            background:${badge.bg};border:1px solid ${badge.border};color:${badge.color};
            padding:4px 12px;border-radius:6px;font-size:0.75rem;font-weight:700;text-transform:uppercase;
        ">${profile.role}</span>
        <span style="color:#8a9bb5;font-size:0.8rem;">👤 ${profile.full_name || profile.email}</span>
        <button id="logoutBtnAuth" style="
            background:rgba(255,68,102,0.12);border:1px solid rgba(255,68,102,0.25);color:#ff4466;
            padding:6px 14px;border-radius:8px;font-size:0.78rem;font-weight:600;cursor:pointer;
            font-family:inherit;transition:all 0.3s;
        ">Logout</button>
    `;
    nav.style.position = 'relative';
    nav.appendChild(section);

    document.getElementById('logoutBtnAuth').addEventListener('click', logout);
}
