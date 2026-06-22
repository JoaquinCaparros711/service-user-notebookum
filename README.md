# 👤 Service User NotebookUm

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0+-darkgreen.svg?style=flat-square&logo=flask&logoColor=white)
![Consul](https://img.shields.io/badge/Consul-1.15+-red.svg?style=flat-square&logo=hashicorp&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.0+-red.svg?style=flat-square&logo=redis&logoColor=white)

Este microservicio se encarga de la **Gestión de Usuarios y la Autenticación** dentro de la plataforma de aprendizaje NotebookUm. Centraliza el flujo de creación de perfiles, validación de credenciales y seguridad mediante tokens JWT.

---

## 📋 Responsabilidades

- **Gestión de Cuentas:** Registro, actualización de perfil, obtención y eliminación de usuarios.
- **Autenticación y Sesión:** Generación y verificación de tokens de acceso JWT (Access Tokens) y de refresco (Refresh Tokens).
- **Capa de Caché:** Implementación de caché de lectura acelerada sobre Redis para reducir la latencia de las consultas frecuentes de perfil.
- **Integración con Persistencia:** Comunicación directa y segura mediante un cliente HTTP dedicado contra el microservicio de persistencia centralizada.

---

## ⚡ Características Clave

- **Seguridad Criptográfica:** Hashing de contraseñas mediante **Bcrypt** con salting dinámico antes del almacenamiento.
- **Autenticación Robusta:** Soporte de flujo JWT completo (firma `HS256`, expiración corta de acceso y ciclo largo para refresh tokens).
- **Consul KV dinámico:** Lectura e inyección transparente en tiempo de ejecución de variables sensibles desde el almacén de configuración de HashiCorp Consul.
- **Auto-registro en Consul:** Hilo en segundo plano que inscribe dinámicamente la instancia del servicio con sus respectivos tags y health-checks HTTP en Consul para la resolución por Traefik.
- **Arquitectura Limpia:** Separación estricta de responsabilidades (Routing -> Service -> Crypto / Persistence / Cache / JWT).

---

## 🌐 Endpoints de la API

Todas las rutas están agrupadas bajo el prefijo `/api/v1/users`:

| Método | Ruta | Autenticación | Descripción |
| :--- | :--- | :---: | :--- |
| **POST** | `/api/v1/users` | Ninguna | Crea una nueva cuenta de usuario en el sistema. |
| **POST** | `/api/v1/users/login` | Ninguna | Valida credenciales y genera un par de tokens JWT (access y refresh). |
| **POST** | `/api/v1/users/refresh` | Ninguna | Valida un `refresh_token` y expide un nuevo access token. |
| **GET** | `/api/v1/users/<id>` | Ninguna / Interna | Obtiene los detalles de un usuario por su ID (consulta cacheada en Redis). |
| **PATCH** | `/api/v1/users/<id>` | **JWT Bearer** | Modifica información básica del usuario o actualiza su contraseña. |
| **DELETE** | `/api/v1/users/<id>` | **JWT Bearer** | Elimina permanentemente la cuenta de usuario del sistema. |
| **GET** | `/api/v1/users/ping-redis` | Ninguna | Endpoint de diagnóstico técnico de conectividad con Redis. |

---

## ⚙️ Configuración centralizada (Consul KV)

El microservicio resuelve sus configuraciones dinámicamente consultando la clave raíz `notebookum/user` en Consul. Si Consul no responde o la clave no existe, se emplean los siguientes valores de respaldo:

| Clave en Consul KV | Variable de Entorno Local | Valor por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `secret_key` | `SECRET_KEY` | `dev-secret-key` | Semilla criptográfica utilizada para firmar los tokens JWT. |
| `persistence_url` | `PERSISTENCE_URL` | `http://persistence-java.universidad.localhost:8080` | URL base del servicio de persistencia de datos persistentes. |
| `redis_url` | `REDIS_URL` | `redis://redis:6379/0` | URL de conexión para la instancia de caché de Redis. |
| `jwt_expiration_seconds`| `JWT_EXPIRATION_SECONDS`| `3600` (1 hora) | Tiempo de validez del token de acceso generado en el login. |
| `jwt_refresh_expiration_days`| `JWT_REFRESH_EXPIRATION_DAYS`| `7` (7 días) | Tiempo de validez del token de refresco. |

---

## 🚀 Despliegue y Ejecución

### Requisitos Previos

- Python 3.11 o superior.
- Instancia activa de Consul (`http://localhost:8500`).
- Instancia activa de Redis (`redis://localhost:6379`).

### Ejecución Local (Desarrollo)

1. Crear un entorno virtual e instalar las dependencias:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Ejecutar la aplicación mediante Flask CLI:
   ```bash
   export FLASK_ENV=development
   export CONSUL_URL=http://localhost:8500
   flask run --port=5004
   ```

### Despliegue en Docker

El microservicio está preparado para un despliegue multi-réplica detrás del balanceador de carga Traefik, autogestionando sus metadatos de red a través de Consul.

```bash
docker-compose up -d --build
```

El servicio se registrará con la IP asignada por Docker y responderá dinámicamente a través del enrutador configurado por Consul.
