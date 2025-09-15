   // Alternar submenú al hacer clic
        document.querySelectorAll('.dropdown').forEach(drop => {
            drop.addEventListener('click', function(e) {
                if (e.target.closest('.menu-item')) {
                    e.preventDefault();
                    this.querySelector('.submenu').classList.toggle('show');
                }
            });
        });

        // Cerrar submenús al hacer clic fuera
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.dropdown')) {
                document.querySelectorAll('.submenu').forEach(menu => menu.classList.remove('show'));
            }
        });