# Variables de Entorno para Railway

Estas son las variables de entorno que debes configurar en Railway Dashboard:

## Variables Obligatorias

### Base de Datos
- `DATABASE_URL` - Se configura automáticamente por Railway cuando agregas PostgreSQL

### Django
- `SECRET_KEY` - Tu secret key de Django
- `DEBUG` - `False` para producción

### Firebase (Nuevas para notificaciones push)
- `FIREBASE_PROJECT_ID` - `smart-condominium-d84b9`
- `FIREBASE_CREDENTIALS_JSON` - El contenido completo del archivo firebase-credentials.json como string JSON

### AWS (Para reconocimiento facial)
- `AWS_ACCESS_KEY_ID` - Tu access key de AWS
- `AWS_SECRET_ACCESS_KEY` - Tu secret key de AWS
- `AWS_DEFAULT_REGION` - `us-east-1`
- `REKOGNITION_COLLECTION_ID` - `condominio-faces`

### Google Vision (Para OCR)
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` - Credenciales de Google Cloud como JSON string

## Cómo agregar FIREBASE_CREDENTIALS_JSON en Railway

1. Ve a tu proyecto en Railway Dashboard
2. Ve a Variables
3. Agrega una nueva variable llamada `FIREBASE_CREDENTIALS_JSON`
4. Copia TODO el contenido del archivo firebase-credentials.json y pégalo como valor
5. Asegúrate de que sea un JSON válido (debe empezar con { y terminar con })

## Pasos Post-Despliegue (IMPORTANTE)

Una vez que el código esté desplegado en Railway, debes ejecutar estos comandos **EN RAILWAY**, no en tu terminal local:

**En Railway Dashboard:**
1. Ve a tu proyecto > Deployments
2. Busca "Run Command" o el ícono de terminal
3. Ejecuta estos comandos:

   ```bash
   python manage.py migrate
   ```

   ```bash
   python manage.py create_notification_templates
   ```

4. **Verificar que todo funciona:**
   - `https://backend-condo-production.up.railway.app/api/health/` (público)
   - `https://backend-condo-production.up.railway.app/api/notifications/api/templates/` (requiere autenticación)

## Endpoints de Notificaciones

- `POST /api/notifications/api/fcm-token/` - Registrar token FCM
- `GET /api/notifications/api/notifications/` - Listar notificaciones del usuario
- `GET /api/notifications/api/unread/` - Notificaciones no leídas
- `GET /api/notifications/api/templates/` - Plantillas (admin)