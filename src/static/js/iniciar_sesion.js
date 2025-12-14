document.addEventListener("DOMContentLoaded", () => {
    const togglePassword = document.querySelector(".toggle-password");
    const passwordField = document.getElementById("password");

    togglePassword.addEventListener("click", () => {
        const isPassword = passwordField.getAttribute("type") === "password";
        passwordField.setAttribute("type", isPassword ? "text" : "password");

        // Cambiar icono del ojo
        togglePassword.classList.toggle("fa-eye");
        togglePassword.classList.toggle("fa-eye-slash");
    });
});