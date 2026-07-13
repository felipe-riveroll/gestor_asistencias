# core/decorators.py
"""Decoradores de autorización reutilizables.

`group_required` es la primitiva de control de acceso por grupo de Django.
Apilar SIEMPRE encima de `@login_required` (login primero, grupo después):
la autenticación nunca autoriza por sí sola.
"""
from functools import wraps

from django.http import HttpResponseForbidden


def group_required(*group_names):
    """Permite el acceso sólo a usuarios autenticados que pertenezcan a alguno
    de los grupos indicados. Devuelve 403 en caso contrario."""

    def decorator(view):
        @wraps(view)
        def _wrapper(request, *args, **kwargs):
            user = request.user
            if (
                user.is_authenticated
                and user.groups.filter(name__in=group_names).exists()
            ):
                return view(request, *args, **kwargs)
            return HttpResponseForbidden("No tienes permisos para esta operación.")

        return _wrapper

    return decorator
