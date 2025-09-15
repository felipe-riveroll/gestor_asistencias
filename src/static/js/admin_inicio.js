/*// Base de datos temporal
let admins = [
    { 
        id: 1, 
        firstName: "Juan", 
        firstLastName: "Pérez", 
        secondLastName: "Gómez", 
        email: "juan@example.com" 
    },
    { 
        id: 2, 
        firstName: "María", 
        firstLastName: "García", 
        secondLastName: "López", 
        email: "maria@example.com" 
    }
];

// Variables para controlar el estado
let isEditing = false;
let currentAdminId = null;

// Elementos del DOM
const adminForm = document.getElementById('adminForm');
const firstNameInput = document.getElementById('firstName');
const firstLastNameInput = document.getElementById('firstLastName');
const secondLastNameInput = document.getElementById('secondLastName');
const emailInput = document.getElementById('email');
const formTitle = document.getElementById('formTitle');
const cancelBtn = document.getElementById('cancelBtn');
const adminsTable = document.querySelector('#adminsTable tbody');
const confirmModal = document.getElementById('confirmModal');
const modalMessage = document.getElementById('modalMessage');
const modalConfirm = document.getElementById('modalConfirm');
const modalCancel = document.getElementById('modalCancel');
const closeModal = document.querySelector('.close-modal');

// Expresión regular para validar solo letras y espacios
const lettersOnlyRegex = /^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$/;

// Inicializar la aplicación
document.addEventListener('DOMContentLoaded', () => {
    renderAdminsTable();
    setupEventListeners();
});

// Configurar validación y bloqueo de teclas no permitidas
function setupInputValidation() {
    [firstNameInput, firstLastNameInput, secondLastNameInput].forEach(input => {
        
        // Bloquear números y símbolos al teclear
        input.addEventListener('keydown', (e) => {
            const allowedKeys = [
                'Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab', 'Home', 'End'
            ];

            // Permitir teclas especiales o combinaciones como Ctrl+C, Ctrl+V
            if (
                allowedKeys.includes(e.key) ||
                (e.ctrlKey || e.metaKey) // Atajos
            ) {
                return;
            }

            // Bloquear cualquier tecla que no sea letra o espacio
            if (!/^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]$/.test(e.key)) {
                e.preventDefault();
            }
        });

        // Validación visual en tiempo real
        input.addEventListener('input', (e) => {
            const value = e.target.value;
            const isValid = value === "" || lettersOnlyRegex.test(value);
            const errorElement = document.getElementById(`${e.target.id}Error`);
            
            if (!isValid) {
                e.target.classList.add('error');
                errorElement.style.display = 'block';
            } else {
                e.target.classList.remove('error');
                errorElement.style.display = 'none';
            }
        });
    });
}

// Configurar event listeners
function setupEventListeners() {
    setupInputValidation();
    
    // Formulario
    adminForm.addEventListener('submit', handleFormSubmit);
    
    // Botón cancelar
    cancelBtn.addEventListener('click', resetForm);
    
    // Modal
    modalConfirm.addEventListener('click', handleModalConfirm);
    modalCancel.addEventListener('click', closeConfirmModal);
    closeModal.addEventListener('click', closeConfirmModal);
    
    // Cerrar modal al hacer clic fuera
    confirmModal.addEventListener('click', (e) => {
        if (e.target === confirmModal) closeConfirmModal();
    });
}

// Renderizar la tabla de administradores
function renderAdminsTable() {
    adminsTable.innerHTML = admins.map(admin => `
        <tr>
            <td>${admin.id}</td>
            <td>${admin.firstName} ${admin.firstLastName} ${admin.secondLastName || ''}</td>
            <td>${admin.email}</td>
            <td class="actions">
                <button class="action-btn edit-btn" onclick="editAdmin(${admin.id})">
                    <i class="fas fa-edit"></i> Editar
                </button>
                <button class="action-btn delete-btn" onclick="showDeleteConfirm(${admin.id})">
                    <i class="fas fa-trash-alt"></i> Eliminar
                </button>
            </td>
        </tr>
    `).join('');
}

// Validar formulario
function validateForm() {
    let isValid = true;
    
    if (!lettersOnlyRegex.test(firstNameInput.value) || firstNameInput.value === "") {
        firstNameInput.classList.add('error');
        document.getElementById('firstNameError').style.display = 'block';
        isValid = false;
    }
    
    if (!lettersOnlyRegex.test(firstLastNameInput.value) || firstLastNameInput.value === "") {
        firstLastNameInput.classList.add('error');
        document.getElementById('firstLastNameError').style.display = 'block';
        isValid = false;
    }
    
    if (secondLastNameInput.value !== "" && !lettersOnlyRegex.test(secondLastNameInput.value)) {
        secondLastNameInput.classList.add('error');
        document.getElementById('secondLastNameError').style.display = 'block';
        isValid = false;
    }
    
    return isValid;
}

// Manejar envío del formulario
function handleFormSubmit(e) {
    e.preventDefault();
    
    if (!validateForm()) {
        showFeedback("❌ Por favor corrige los errores en el formulario");
        return;
    }
    
    const id = document.getElementById('adminId').value;
    const adminData = {
        firstName: firstNameInput.value.trim(),
        firstLastName: firstLastNameInput.value.trim(),
        secondLastName: secondLastNameInput.value.trim(),
        email: emailInput.value.trim()
    };
    
    if (isEditing) {
        updateAdmin(id, adminData);
    } else {
        createAdmin(adminData);
    }
}

// Crear nuevo administrador
function createAdmin(adminData) {
    const newAdmin = {
        id: admins.length > 0 ? Math.max(...admins.map(a => a.id)) + 1 : 1,
        ...adminData
    };
    
    admins.push(newAdmin);
    renderAdminsTable();
    adminForm.reset();
    showFeedback('✅ Administrador creado exitosamente!');
}

// Actualizar administrador
function updateAdmin(id, adminData) {
    const index = admins.findIndex(a => a.id == id);
    if (index !== -1) {
        admins[index] = { ...admins[index], ...adminData };
        renderAdminsTable();
        resetForm();
        showFeedback('✏️ Administrador actualizado exitosamente!');
    }
}

// Editar administrador
function editAdmin(id) {
    const admin = admins.find(a => a.id == id);
    if (admin) {
        isEditing = true;
        currentAdminId = id;
        
        formTitle.innerHTML = `<i class="fas fa-user-edit"></i><span>Editar administrador</span>`;
        cancelBtn.style.display = 'block';
        
        document.getElementById('adminId').value = admin.id;
        firstNameInput.value = admin.firstName;
        firstLastNameInput.value = admin.firstLastName;
        secondLastNameInput.value = admin.secondLastName || '';
        emailInput.value = admin.email;
        
        document.querySelector('.form-container').scrollIntoView({ behavior: 'smooth' });
    }
}

// Mostrar confirmación de eliminación
function showDeleteConfirm(id) {
    const admin = admins.find(a => a.id == id);
    if (admin) {
        currentAdminId = id;
        const fullName = `${admin.firstName} ${admin.firstLastName} ${admin.secondLastName || ''}`;
        modalMessage.textContent = `¿Estás seguro de eliminar a ${fullName}?`;
        confirmModal.style.display = 'flex';
    }
}

// Manejar confirmación del modal
function handleModalConfirm() {
    deleteAdmin(currentAdminId);
    closeConfirmModal();
}

// Eliminar administrador
function deleteAdmin(id) {
    admins = admins.filter(admin => admin.id != id);
    renderAdminsTable();
    showFeedback('🗑️ Administrador eliminado exitosamente!');
}

// Cerrar modal
function closeConfirmModal() {
    confirmModal.style.display = 'none';
    currentAdminId = null;
}

// Resetear formulario
function resetForm() {
    isEditing = false;
    currentAdminId = null;
    adminForm.reset();
    document.getElementById('adminId').value = '';
    formTitle.innerHTML = `<i class="fas fa-user-plus"></i><span>Agregar nuevo administrador</span>`;
    cancelBtn.style.display = 'none';
    
    document.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
    document.querySelectorAll('.error-message').forEach(el => el.style.display = 'none');
}

// Mostrar feedback
function showFeedback(message) {
    alert(message);
}*/