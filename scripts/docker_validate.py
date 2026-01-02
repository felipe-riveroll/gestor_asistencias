#!/usr/bin/env python3
"""
Script de validación específico para entornos Docker
Verifica configuraciones de seguridad en contenedores
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# Colores para output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class DockerValidator:
    """Validador de configuración para Docker"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed = []

    def log_error(self, message: str):
        """Registrar error crítico"""
        self.errors.append(message)
        print(f"{RED}❌ ERROR: {message}{RESET}")

    def log_warning(self, message: str):
        """Registrar advertencia"""
        self.warnings.append(message)
        print(f"{YELLOW}⚠️  WARNING: {message}{RESET}")

    def log_passed(self, message: str):
        """Registrar prueba pasada"""
        self.passed.append(message)
        print(f"{GREEN}✅ PASSED: {message}{RESET}")

    def log_info(self, message: str):
        """Registrar información"""
        print(f"{BLUE}ℹ️  INFO: {message}{RESET}")

    def validate_dockerfile_security(self) -> bool:
        """Validar seguridad del Dockerfile"""
        self.log_info("Validando Dockerfile...")

        dockerfile = Path('Dockerfile')
        if not dockerfile.exists():
            self.log_error("No se encontró Dockerfile")
            return False

        with open(dockerfile, 'r') as f:
            lines = f.readlines()

        content = ''.join(lines)

        # Verificar que no se copie .env
        if 'COPY .env' in content or 'COPY .' in content:
            self.log_warning("Verifica que el Dockerfile no copie archivos .env")

        # Verificar usuario no-root
        if 'USER' in content:
            self.log_passed("Dockerfile define usuario no-root")
        else:
            self.log_warning("Dockerfile debería definir usuario no-root para seguridad")

        # Verificar que no instale paquetes innecesarios
        if 'apt-get' in content:
            if 'rm -rf /var/lib/apt/lists/*' in content:
                self.log_passed("Se limpian cachés de apt")
            else:
                self.log_warning("Deberías limpiar el caché de apt después de instalar")

        # Verificar variables de entorno
        if 'ENV PYTHONDONTWRITEBYTECODE=1' in content:
            self.log_passed("PYTHONDONTWRITEBYTECODE configurado")
        else:
            self.log_warning("Agrega PYTHONDONTWRITEBYTECODE=1 para optimizar")

        if 'ENV PYTHONUNBUFFERED=1' in content:
            self.log_passed("PYTHONUNBUFFERED configurado")
        else:
            self.log_warning("Agrega PYTHONUNBUFFERED=1 para mejores logs")

        return True

    def validate_docker_compose_security(self) -> bool:
        """Validar seguridad de docker-compose.yml"""
        self.log_info("Validando docker-compose.yml...")

        compose_file = Path('docker-compose.yml')
        if not compose_file.exists():
            self.log_info("No se encontró docker-compose.yml")
            return True

        try:
            import yaml
            with open(compose_file, 'r') as f:
                compose = yaml.safe_load(f)

            # Verificar que no exponga puerto de DB a host en producción
            services = compose.get('services', {})

            for service_name, service_config in services.items():
                if 'db' in service_name.lower() or 'database' in service_name.lower():
                    ports = service_config.get('ports', [])
                    for port in ports:
                        if '5432' in str(port):
                            self.log_warning(f"Servicio {service_name} expone puerto de BD - considera usar networks")

                # Verificar variables de entorno
                env_file = service_config.get('env_file')
                if env_file:
                    self.log_passed(f"Servicio {service_name} usa archivo de entorno")
                else:
                    self.log_info(f"Servicio {service_name} no especifica env_file")

            # Verificar networks
            networks = compose.get('networks', {})
            if networks:
                self.log_passed("Se definen networks personalizadas")
            else:
                self.log_info("Usando network por defecto")

            return True

        except ImportError:
            self.log_info("PyYAML no instalado - validación básica")
            return True
        except Exception as e:
            self.log_error(f"Error al validar docker-compose.yml: {e}")
            return False

    def validate_container_security(self) -> bool:
        """Validar configuraciones de seguridad del contenedor"""
        self.log_info("Validando configuraciones de seguridad del contenedor...")

        # Verificar variables de entorno de seguridad
        security_envs = [
            'DJANGO_SETTINGS_MODULE',
            'PYTHONDONTWRITEBYTECODE',
            'PYTHONUNBUFFERED'
        ]

        for env in security_envs:
            if os.getenv(env):
                self.log_passed(f"Variable {env} configurada")

        # Verificar que DEBUG esté en False
        debug = os.getenv('DEBUG', 'False')
        if debug.lower() == 'true':
            self.log_error("DEBUG está en True - debe ser False en producción")
        else:
            self.log_passed("DEBUG está en False")

        return True

    def validate_volumes_and_secrets(self) -> bool:
        """Validar volúmenes y manejo de secretos"""
        self.log_info("Validando volúmenes y secretos...")

        compose_file = Path('docker-compose.yml')
        if compose_file.exists():
            try:
                import yaml
                with open(compose_file, 'r') as f:
                    compose = yaml.safe_load(f)

                services = compose.get('services', {})

                for service_name, service_config in services.items():
                    volumes = service_config.get('volumes', [])

                    for volume in volumes:
                        volume_str = str(volume)
                        if '.env' in volume_str and 'ro' not in volume_str:
                            self.log_warning(f"Volumen {volume} no es read-only - considera agregar ':ro'")

                    # Verificar que no se monten secretos en volúmenes
                    for volume in volumes:
                        if '.env' in str(volume):
                            self.log_info(f"Servicio {service_name} monta .env - asegúrate de que sea seguro")

            except Exception as e:
                self.log_error(f"Error al validar volúmenes: {e}")

        return True

    def validate_network_security(self) -> bool:
        """Validar configuración de redes"""
        self.log_info("Validando configuración de redes...")

        compose_file = Path('docker-compose.yml')
        if compose_file.exists():
            try:
                import yaml
                with open(compose_file, 'r') as f:
                    compose = yaml.safe_load(f)

                networks = compose.get('networks', {})

                if not networks:
                    self.log_info("Usando network bridge por defecto")
                    return True

                for network_name, network_config in networks.items():
                    driver = network_config.get('driver', 'bridge')

                    if driver == 'bridge':
                        self.log_passed(f"Network {network_name} usa driver bridge")
                    elif driver == 'host':
                        self.log_warning(f"Network {network_name} usa driver host - revisa seguridad")
                    elif driver == 'overlay':
                        self.log_info(f"Network {network_name} usa driver overlay")

                    # Verificar configuración de IPAM
                    ipam = network_config.get('ipam', {})
                    if ipam:
                        self.log_info(f"Network {network_name} tiene configuración IPAM personalizada")

            except Exception as e:
                self.log_error(f"Error al validar redes: {e}")

        return True

    def validate_resource_limits(self) -> bool:
        """Validar límites de recursos"""
        self.log_info("Validando límites de recursos...")

        compose_file = Path('docker-compose.yml')
        if compose_file.exists():
            try:
                import yaml
                with open(compose_file, 'r') as f:
                    compose = yaml.safe_load(f)

                services = compose.get('services', {})

                for service_name, service_config in services.items():
                    deploy = service_config.get('deploy', {})
                    resources = deploy.get('resources', {})

                    limits = resources.get('limits', {})
                    if limits:
                        self.log_passed(f"Servicio {service_name} tiene límites de recursos")
                    else:
                        self.log_warning(f"Servicio {service_name} no tiene límites de recursos definidos")

                    # Verificar memoria
                    memory = limits.get('memory')
                    if memory:
                        self.log_passed(f"Servicio {service_name} tiene límite de memoria: {memory}")

                    # Verificar CPU
                    cpus = limits.get('cpus')
                    if cpus:
                        self.log_passed(f"Servicio {service_name} tiene límite de CPU: {cpus}")

            except Exception as e:
                self.log_error(f"Error al validar recursos: {e}")

        return True

    def validate_health_checks(self) -> bool:
        """Validar health checks"""
        self.log_info("Validando health checks...")

        compose_file = Path('docker-compose.yml')
        if compose_file.exists():
            try:
                import yaml
                with open(compose_file, 'r') as f:
                    compose = yaml.safe_load(f)

                services = compose.get('services', {})

                for service_name, service_config in services.items():
                    healthcheck = service_config.get('healthcheck', {})

                    if healthcheck:
                        self.log_passed(f"Servicio {service_name} tiene health check")

                        test = healthcheck.get('test')
                        if test:
                            self.log_info(f"Health check: {test}")

                        interval = healthcheck.get('interval')
                        if interval:
                            self.log_info(f"Intervalo: {interval}")
                    else:
                        self.log_warning(f"Servicio {service_name} no tiene health check")

            except Exception as e:
                self.log_error(f"Error al validar health checks: {e}")

        return True

    def generate_docker_report(self) -> str:
        """Generar reporte de validación de Docker"""
        report = []
        report.append("=" * 60)
        report.append("REPORTE DE VALIDACIÓN DE DOCKER")
        report.append("=" * 60)
        report.append(f"Total de pruebas pasadas: {len(self.passed)}")
        report.append(f"Total de advertencias: {len(self.warnings)}")
        report.append(f"Total de errores: {len(self.errors)}")
        report.append("")

        if self.passed:
            report.append("✅ PRUEBAS PASADAS:")
            for item in self.passed:
                report.append(f"  - {item}")
            report.append("")

        if self.warnings:
            report.append("⚠️  ADVERTENCIAS:")
            for item in self.warnings:
                report.append(f"  - {item}")
            report.append("")

        if self.errors:
            report.append("❌ ERRORES CRÍTICOS:")
            for item in self.errors:
                report.append(f"  - {item}")
            report.append("")

        if not self.errors:
            report.append("🐳 CONFIGURACIÓN DE DOCKER SEGURA")
            report.append("La configuración es adecuada para producción.")
        else:
            report.append("🚨 CONFIGURACIÓN DE DOCKER INSEGURA")
            report.append("Corrige los errores antes del despliegue.")

        return "\n".join(report)

    def run_all_validations(self) -> bool:
        """Ejecutar todas las validaciones de Docker"""
        print(f"{BLUE}Iniciando validación de configuración Docker...{RESET}")
        print("=" * 60)

        # Cargar variables de entorno
        from dotenv import load_dotenv
        load_dotenv()

        # Ejecutar validaciones
        validations = [
            self.validate_dockerfile_security,
            self.validate_docker_compose_security,
            self.validate_container_security,
            self.validate_volumes_and_secrets,
            self.validate_network_security,
            self.validate_resource_limits,
            self.validate_health_checks,
        ]

        all_passed = True
        for validation in validations:
            try:
                if not validation():
                    all_passed = False
            except Exception as e:
                self.log_error(f"Error en validación: {e}")
                all_passed = False

        print("\n" + "=" * 60)
        print(self.generate_docker_report())

        return all_passed and len(self.errors) == 0


def main():
    """Función principal"""
    validator = DockerValidator()
    success = validator.run_all_validations()

    # Salir con código apropiado
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()