# Smart Condominium Backend

Backend del sistema Smart Condominium desarrollado con Django y Django REST Framework.

## Características

- **Django 4.2+** con Django REST Framework
- **Autenticación JWT** con refresh tokens
- **Modelos personalizados** para usuarios, roles y permisos
- **API RESTful** documentada con Swagger/OpenAPI
- **CORS** configurado para desarrollo frontend
- **Base de datos** configurable (PostgreSQL/SQLite)

## Estructura de Apps

### 🔐 Authentication (`apps/authentication`)
- Autenticación JWT
- Registro de usuarios
- Gestión de sesiones
- Cambio de contraseñas

### 👥 Users (`apps/users`) 
- Modelo de usuario extendido
- Sistema de roles y permisos
- Gestión de perfiles

### 🏢 Properties (`apps/properties`)
- Unidades habitacionales
- Propietarios y residentes
- Historial de propietarios

### 📢 Communications (`apps/communications`)
- Avisos y comunicados
- Sistema de lectura de avisos

### ⚙️ Core (`apps/core`)
- Modelos base (Condominio, Bloque)
- Configuraciones del sistema
- Utilidades comunes

## Configuración

### Variables de Entorno (.env)

```env
SECRET_KEY=tu-secret-key-aqui
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Instalación

1. Crear entorno virtual:
```bash
python -m venv venv
```

2. Activar entorno virtual:
```bash
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Ejecutar migraciones:
```bash
python manage.py makemigrations
python manage.py migrate
```

5. Crear superusuario:
```bash
python manage.py createsuperuser
```

6. Ejecutar servidor:
```bash
python manage.py runserver
```

## API Endpoints

### 🔐 Autenticación
- `POST /api/auth/login/` - Iniciar sesión
- `POST /api/auth/register/` - Registrar usuario
- `POST /api/auth/logout/` - Cerrar sesión
- `POST /api/auth/token/refresh/` - Refrescar token
- `GET /api/auth/profile/` - Obtener perfil
- `PUT /api/auth/profile/update/` - Actualizar perfil

### 📚 Documentación API
- `GET /api/swagger/` - Documentación Swagger UI
- `GET /api/redoc/` - Documentación ReDoc
- `GET /api/schema/` - Schema OpenAPI

## Modelos Principales

### Usuario (User)
- Extiende AbstractUser
- Campos adicionales: teléfono, cédula, avatar
- Relaciones con condominio y rol

### Condominio
- Información básica del condominio
- Relación con bloques y usuarios

### UnidadHabitacional 
- Departamentos/casas
- Relación con bloque
- Propietarios y residentes

### Role & Permission
- Sistema flexible de roles y permisos
- Relación muchos a muchos

## Comandos Útiles

```bash
# Verificar configuración
python manage.py check

# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Shell interactivo
python manage.py shell

# Recolectar archivos estáticos
python manage.py collectstatic
```

## Estado del Proyecto

✅ **Completado:**
- Estructura de apps Django
- Modelos de datos
- Sistema de autenticación JWT
- Configuración básica
- Migraciones
- Usuario administrador

🚧 **Pendiente:**
- ViewSets y serializers completos
- Permisos granulares
- Tests unitarios
- Configuración de producción
- Integración con PostgreSQL
- Frontend React

## Credenciales de Desarrollo

- **Usuario:** admin
- **Email:** admin@smartcondo.com  
- **Contraseña:** admin123

## Tecnologías

- Django 4.2+
- Django REST Framework
- Django CORS Headers
- JWT Authentication
- PostgreSQL/SQLite
- Python Decouple