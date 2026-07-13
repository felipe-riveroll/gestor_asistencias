// Helper central de token CSRF para peticiones AJAX (fetch/XHR).
//
// Lee primero la cookie `csrftoken` (cuando CSRF_COOKIE_HTTPONLY=False) y, si no está
// disponible (cookie HttpOnly), cae al <meta name="csrf-token"> que las plantillas
// inyectan vía {{ csrf_token }}. Debe cargarse ANTES que cualquier JS de página.
function getCSRFToken() {
    // 1) Cookie (legible solo si CSRF_COOKIE_HTTPONLY=False)
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 10) === 'csrftoken=') {
                return decodeURIComponent(cookie.substring(10));
            }
        }
    }
    // 2) Meta tag (funciona con CSRF_COOKIE_HTTPONLY=True)
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) {
        return meta.getAttribute('content');
    }
    return null;
}

// Indica si un método HTTP es "seguro" (no requiere token CSRF).
function csrfSafeMethod(method) {
    return /^(GET|HEAD|OPTIONS|TRACE)$/i.test(method);
}
