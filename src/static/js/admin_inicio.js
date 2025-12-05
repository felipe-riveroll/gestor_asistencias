/* Lógica para el Modal de Contraseña y Envío AJAX 
*/

// ==========================================
// 1. FUNCIONES GLOBALES (Para que funcionen los onclick del HTML)
// ==========================================

function openPasswordModal() {
    const modal = document.getElementById('passwordModal');
    if (modal) {
        modal.style.display = 'block';
        // Limpiar campos por seguridad
        const newPass = document.getElementById('newPassword');
        const confirmPass = document.getElementById('confirmPassword');
        if (newPass) newPass.value = '';
        if (confirmPass) confirmPass.value = '';
    }
}

function closePasswordModal() {
    const modal = document.getElementById('passwordModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function togglePassword(inputId, icon) {
    const input = document.getElementById(inputId);
    if (input && input.type === "password") {
        input.type = "text";
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else if (input) {
        input.type = "password";
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

// Cerrar modales al hacer clic fuera
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = "none";
    }
}

// ==========================================
// 2. LÓGICA DE ENVÍO (Se ejecuta al cargar la página)
// ==========================================

document.addEventListener('DOMContentLoaded', function() {
    
    const form = document.getElementById('passwordForm');

    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault(); // Detener recarga

            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;

            // Validación básica
            if (newPassword !== confirmPassword) {
                alert('Las contraseñas no coinciden.');
                return;
            }

            // Obtener CSRF Token
            function getCookie(name) {
                let cookieValue = null;
                if (document.cookie && document.cookie !== '') {
                    const cookies = document.cookie.split(';');
                    for (let i = 0; i < cookies.length; i++) {
                        const cookie = cookies[i].trim();
                        if (cookie.substring(0, name.length + 1) === (name + '=')) {
                            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                            break;
                        }
                    }
                }
                return cookieValue;
            }
            const csrftoken = getCookie('csrftoken');

            // Validar que la URL global exista (prevención de errores)
            if (typeof URL_CAMBIAR_PASSWORD === 'undefined') {
                console.error('Error: La variable URL_CAMBIAR_PASSWORD no está definida en el HTML.');
                alert('Error de configuración en el sistema.');
                return;
            }

            // Enviar petición
            fetch(URL_CAMBIAR_PASSWORD, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({
                    newPassword: newPassword,
                    confirmPassword: confirmPassword
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message); // Muestra "Contraseña actualizada con éxito"
                    closePasswordModal();
                    form.reset();
                } else {
                    alert('Error: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Hubo un error al conectar con el servidor.');
            });
        });
    }
});