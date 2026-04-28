# Service User NotebookUm

Este microservicio se encarga de la **Gestión de Usuarios y Autenticación** para el sistema NotebookUm.

## Responsabilidades
- Maneja la creación de cuentas de usuario, inicio de sesión y perfiles.
- Se comunica con el servicio de Persistencia para almacenar y recuperar la información del usuario de la base de datos.
- Puede generar tokens JWT (si se implementa) para autenticar las peticiones del Gateway.

## Ejecución con Docker
```bash
docker-compose up -d --build
```
El servicio estará disponible internamente en el puerto `5004`.
