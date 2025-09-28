from rest_framework import serializers
from .models import Vehicle, VehicleAccessLog, PersonProfile, FacialAccessLog
from apps.users.serializers import UserSerializer


class VehicleSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Vehicle.
    """
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            'id', 'user', 'user_name', 'placa', 'color',
            'modelo', 'marca', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_placa(self, value):
        """
        Validar formato de placa boliviana.
        """
        import re

        # Patrones válidos para placas bolivianas
        patterns = [
            r'^\d{4}-[A-Z]{3}$',  # 1234-ABC
            r'^\d{3}-[A-Z]{3}$',  # 123-ABC
            r'^[A-Z]{3}-\d{3}$',  # ABC-123
        ]

        value_upper = value.upper()

        for pattern in patterns:
            if re.match(pattern, value_upper):
                return value_upper

        raise serializers.ValidationError(
            "Formato de placa inválido. Use formatos: 1234-ABC, 123-ABC o ABC-123"
        )


class VehicleAccessLogSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo VehicleAccessLog.
    """
    vehicle_info = VehicleSerializer(source='vehicle', read_only=True)

    class Meta:
        model = VehicleAccessLog
        fields = [
            'id', 'vehicle', 'vehicle_info', 'placa_detectada',
            'confianza_ocr', 'resultado', 'imagen', 'timestamp_evento',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'timestamp_evento']


class VehicleOCRRequestSerializer(serializers.Serializer):
    """
    Serializer para procesar requests de OCR de vehículos.
    """
    imagen = serializers.ImageField()

    def validate_imagen(self, value):
        """
        Validar que la imagen tenga formato y tamaño válidos.
        """
        # Validar tamaño máximo (10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                "El archivo es demasiado grande. Máximo 10MB permitido."
            )

        # Validar formato
        valid_formats = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp']
        if value.content_type not in valid_formats:
            raise serializers.ValidationError(
                "Formato de imagen inválido. Use JPEG, PNG o BMP."
            )

        return value


class VehicleOCRResponseSerializer(serializers.Serializer):
    """
    Serializer para respuestas de OCR de vehículos.
    """
    success = serializers.BooleanField()
    plate = serializers.CharField(max_length=20, allow_null=True)
    confidence = serializers.DecimalField(max_digits=5, decimal_places=2)
    resultado = serializers.CharField(max_length=20)
    message = serializers.CharField(max_length=200)
    vehicle_info = VehicleSerializer(allow_null=True)
    extracted_text = serializers.CharField(max_length=500, allow_null=True)
    access_log_id = serializers.IntegerField(allow_null=True)


class VehicleOCRTrainingSerializer(serializers.Serializer):
    """
    Serializer para entrenar el OCR con correcciones manuales.
    """
    access_log_id = serializers.IntegerField()
    placa_correcta = serializers.CharField(max_length=20)

    def validate_placa_correcta(self, value):
        """
        Validar formato de placa boliviana.
        """
        import re

        # Limpiar y normalizar
        value_clean = value.strip().upper()

        # Patrones válidos para placas bolivianas
        patterns = [
            r'^\d{4}-[A-Z]{3}$',  # 1234-ABC
            r'^\d{3}-[A-Z]{3}$',  # 123-ABC
            r'^[A-Z]{3}-\d{3}$',  # ABC-123
            r'^\d{4}[A-Z]{3}$',   # 1234ABC (sin guión)
            r'^\d{3}[A-Z]{3}$',   # 123ABC (sin guión)
            r'^[A-Z]{3}\d{3}$',   # ABC123 (sin guión)
        ]

        for pattern in patterns:
            if re.match(pattern, value_clean):
                # Normalizar agregando guión si es necesario
                if '-' not in value_clean:
                    if re.match(r'^\d{4}[A-Z]{3}$', value_clean):
                        return f"{value_clean[:4]}-{value_clean[4:]}"
                    elif re.match(r'^\d{3}[A-Z]{3}$', value_clean):
                        return f"{value_clean[:3]}-{value_clean[3:]}"
                    elif re.match(r'^[A-Z]{3}\d{3}$', value_clean):
                        return f"{value_clean[:3]}-{value_clean[3:]}"
                return value_clean

        raise serializers.ValidationError(
            "Formato de placa inválido. Use formatos: 1234-ABC, 123-ABC o ABC-123"
        )


class PersonProfileSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo PersonProfile.
    """
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    person_type_display = serializers.CharField(source='get_person_type_display', read_only=True)

    class Meta:
        model = PersonProfile
        fields = [
            'id', 'name', 'person_type', 'person_type_display', 'photo',
            'is_authorized', 'user', 'user_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'face_encoding']

    def validate_name(self, value):
        """
        Validar que el nombre no esté vacío y tenga formato válido.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre es requerido.")

        value_clean = value.strip()

        if len(value_clean) < 2:
            raise serializers.ValidationError("El nombre debe tener al menos 2 caracteres.")

        if len(value_clean) > 100:
            raise serializers.ValidationError("El nombre no puede exceder 100 caracteres.")

        return value_clean


class FacialAccessLogSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo FacialAccessLog.
    """
    person_info = PersonProfileSerializer(source='person_profile', read_only=True)
    access_result_display = serializers.SerializerMethodField()

    class Meta:
        model = FacialAccessLog
        fields = [
            'id', 'person_profile', 'person_info', 'photo', 'confidence_score',
            'access_granted', 'access_result_display', 'location', 'detected_name',
            'timestamp_evento', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'timestamp_evento']

    def get_access_result_display(self, obj):
        """
        Obtener texto descriptivo del resultado de acceso.
        """
        return obj.get_access_result_display()


class FacialRecognitionRequestSerializer(serializers.Serializer):
    """
    Serializer para procesar requests de reconocimiento facial.
    """
    imagen = serializers.ImageField()
    location = serializers.CharField(max_length=100, required=False, default='Entrada Principal')

    def validate_imagen(self, value):
        """
        Validar que la imagen tenga formato y tamaño válidos.
        """
        # Validar tamaño máximo (10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                "El archivo es demasiado grande. Máximo 10MB permitido."
            )

        # Validar formato
        valid_formats = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp']
        if value.content_type not in valid_formats:
            raise serializers.ValidationError(
                "Formato de imagen inválido. Use JPEG, PNG o BMP."
            )

        return value

    def validate_location(self, value):
        """
        Validar ubicación.
        """
        if value and len(value.strip()) > 100:
            raise serializers.ValidationError(
                "La ubicación no puede exceder 100 caracteres."
            )
        return value.strip() if value else 'Entrada Principal'


class PersonRegistrationSerializer(serializers.Serializer):
    """
    Serializer para registrar nuevas personas.
    """
    imagen = serializers.ImageField()
    name = serializers.CharField(max_length=100)
    person_type = serializers.ChoiceField(choices=PersonProfile.PERSON_TYPE_CHOICES)
    is_authorized = serializers.BooleanField(default=False)
    user = serializers.IntegerField(required=False)

    def validate_imagen(self, value):
        """
        Validar que la imagen tenga formato y tamaño válidos.
        """
        # Validar tamaño máximo (10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                "El archivo es demasiado grande. Máximo 10MB permitido."
            )

        # Validar formato
        valid_formats = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp']
        if value.content_type not in valid_formats:
            raise serializers.ValidationError(
                "Formato de imagen inválido. Use JPEG, PNG o BMP."
            )

        return value

    def validate_name(self, value):
        """
        Validar nombre de la persona.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre es requerido.")

        value_clean = value.strip()

        if len(value_clean) < 2:
            raise serializers.ValidationError("El nombre debe tener al menos 2 caracteres.")

        if len(value_clean) > 100:
            raise serializers.ValidationError("El nombre no puede exceder 100 caracteres.")

        return value_clean


class FacialRecognitionResponseSerializer(serializers.Serializer):
    """
    Serializer para respuestas de reconocimiento facial.
    """
    success = serializers.BooleanField()
    person_profile = PersonProfileSerializer(allow_null=True)
    confidence = serializers.DecimalField(max_digits=5, decimal_places=2)
    access_granted = serializers.BooleanField()
    message = serializers.CharField(max_length=200)
    access_log_id = serializers.IntegerField(allow_null=True)
    error = serializers.CharField(max_length=500, allow_null=True)