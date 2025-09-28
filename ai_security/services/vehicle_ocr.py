import re
import os
from django.conf import settings

try:
    from google.cloud import vision
    import json
    GOOGLE_VISION_AVAILABLE = True
    print("[OCR DEBUG] Google Vision API disponible")
except ImportError as e:
    GOOGLE_VISION_AVAILABLE = False
    print(f"[OCR DEBUG] Google Vision no disponible: {e}")


class VehicleOCRService:
    """
    Servicio para reconocimiento OCR de placas vehiculares bolivianas.
    """

    # Patrones de placas bolivianas
    BOLIVIA_PLATE_PATTERNS = [
        r'\b\d{4}-[A-Z]{3}\b',  # 1234-ABC (formato estándar con guión)
        r'\b\d{3}-[A-Z]{3}\b',  # 123-ABC (formato antiguo con guión)
        r'\b[A-Z]{3}-\d{3}\b',  # ABC-123 (formato especial con guión)
        r'\b\d{4}[A-Z]{3}\b',   # 1234ABC (formato estándar sin guión)
        r'\b\d{3}[A-Z]{3}\b',   # 123ABC (formato antiguo sin guión)
        r'\b[A-Z]{3}\d{3}\b',   # ABC123 (formato especial sin guión)
    ]

    @staticmethod
    def normalize_plate(plate):
        """
        Normaliza una placa al formato estándar con guión.
        """
        if not plate:
            return None

        plate = plate.strip().upper()

        # Si ya tiene guión, devolverla tal como está
        if '-' in plate:
            return plate

        # Agregar guión según el patrón detectado
        if re.match(r'\d{4}[A-Z]{3}', plate):  # 1234ABC -> 1234-ABC
            return f"{plate[:4]}-{plate[4:]}"
        elif re.match(r'\d{3}[A-Z]{3}', plate):  # 123ABC -> 123-ABC
            return f"{plate[:3]}-{plate[3:]}"
        elif re.match(r'[A-Z]{3}\d{3}', plate):  # ABC123 -> ABC-123
            return f"{plate[:3]}-{plate[3:]}"

        return plate

    @staticmethod
    def extract_text_with_google_vision(image_path):
        """
        Extrae texto de placa usando Google Vision API.
        """
        try:
            if not GOOGLE_VISION_AVAILABLE:
                print("[OCR DEBUG] Google Vision no está disponible")
                return None, 0.0

            # Configurar credenciales (desde variable de entorno o archivo local)
            credentials_json = getattr(settings, 'GOOGLE_CLOUD_CREDENTIALS_JSON', None)
            credentials_path = getattr(settings, 'GOOGLE_CLOUD_CREDENTIALS_PATH', None)

            if credentials_json:
                # Usar credenciales desde variable de entorno (producción)
                print("[OCR DEBUG] Usando credenciales de Google Cloud desde variable de entorno")
                try:
                    # Crear archivo temporal con las credenciales
                    import tempfile
                    import json

                    # Validar que el JSON sea válido
                    if isinstance(credentials_json, str):
                        json_data = json.loads(credentials_json)
                    else:
                        json_data = credentials_json

                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                        json.dump(json_data, temp_file)
                        temp_credentials_path = temp_file.name

                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_credentials_path
                    print(f"[OCR DEBUG] Credenciales guardadas en: {temp_credentials_path}")

                except Exception as cred_error:
                    print(f"[OCR DEBUG] Error procesando credenciales JSON: {cred_error}")
                    print(f"[OCR DEBUG] Tipo de credentials_json: {type(credentials_json)}")
                    print(f"[OCR DEBUG] Primeros 100 chars: {str(credentials_json)[:100]}")
                    return None, 0.0
            elif credentials_path and os.path.exists(credentials_path):
                # Usar archivo local (desarrollo)
                print("[OCR DEBUG] Usando credenciales de Google Cloud desde archivo local")
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(credentials_path)
            else:
                print("[OCR DEBUG] Credenciales de Google Cloud no encontradas")
                return None, 0.0

            print("[OCR DEBUG] Enviando imagen a Google Vision...")

            # Crear cliente de Vision
            client = vision.ImageAnnotatorClient()

            # Leer imagen
            with open(image_path, 'rb') as image_file:
                content = image_file.read()

            image = vision.Image(content=content)

            # Extraer texto
            response = client.text_detection(image=image)
            texts = response.text_annotations

            if response.error.message:
                print(f"[OCR DEBUG] Error en Google Vision: {response.error.message}")
                return None, 0.0

            if not texts:
                print("[OCR DEBUG] Google Vision no detectó texto")
                return None, 0.0

            # El primer elemento contiene todo el texto detectado
            detected_text = texts[0].description.strip()
            print(f"[OCR DEBUG] Google Vision texto completo: '{detected_text}'")

            # Buscar patrones de placas en el texto detectado
            lines = detected_text.upper().split('\n')

            # Filtrar líneas que podrían ser placas (longitud entre 6-10 caracteres)
            plate_candidates = []
            for line in lines:
                line_clean = re.sub(r'[^\w-]', '', line.strip())
                if 6 <= len(line_clean) <= 10:
                    # Verificar si parece una placa boliviana
                    if (re.match(r'\d{3,4}[A-Z]{2,3}', line_clean) or
                        re.match(r'\d{3,4}-[A-Z]{2,3}', line_clean) or
                        re.match(r'[A-Z]{2,3}\d{3}', line_clean)):
                        plate_candidates.append(line_clean)
                        print(f"[OCR DEBUG] Candidato de placa: '{line_clean}'")

            # Devolver el mejor candidato
            if plate_candidates:
                best_candidate = plate_candidates[0]
                print(f"[OCR DEBUG] Google Vision detectó placa: '{best_candidate}'")
                return best_candidate, 90.0  # Alta confianza para Google Vision

            print("[OCR DEBUG] Google Vision no encontró patrones de placa válidos")
            return None, 0.0

        except Exception as e:
            print(f"[OCR DEBUG] Error con Google Vision: {e}")
            return None, 0.0

    @staticmethod
    def detect_license_plate(extracted_text):
        """
        Detecta y valida placas bolivianas en el texto extraído.
        """
        if not extracted_text:
            return None, 0.0

        # Limpiar el texto extraído - remover saltos de línea y espacios extras
        cleaned_text = re.sub(r'\s+', ' ', extracted_text.replace('\n', ' ')).strip().upper()
        print(f"[OCR DEBUG] Texto limpio para búsqueda: '{cleaned_text}'")

        # Si el texto es corto y parece una placa directa (probable respuesta de OpenAI)
        if len(cleaned_text) <= 15 and (
            re.match(r'^\d{3,4}-?[A-Z]{2,3}$', cleaned_text) or
            re.match(r'^[A-Z]{2,3}-?\d{3}$', cleaned_text)
        ):
            normalized_plate = VehicleOCRService.normalize_plate(cleaned_text)
            confidence = VehicleOCRService.calculate_plate_confidence(normalized_plate)
            print(f"[OCR DEBUG] Placa detectada directamente: '{normalized_plate}' (probablemente OpenAI)")
            return normalized_plate, confidence

        # Buscar patrones de placas bolivianas estándar
        for pattern in VehicleOCRService.BOLIVIA_PLATE_PATTERNS:
            matches = re.findall(pattern, cleaned_text)
            if matches:
                raw_plate = matches[0].strip()
                normalized_plate = VehicleOCRService.normalize_plate(raw_plate)
                confidence = VehicleOCRService.calculate_plate_confidence(normalized_plate)
                print(f"[OCR DEBUG] Placa encontrada con patrón estándar: '{normalized_plate}'")
                return normalized_plate, confidence

        print(f"[OCR DEBUG] No se encontró placa válida en: '{cleaned_text}'")
        return None, 0.0

    @staticmethod
    def calculate_plate_confidence(plate):
        """
        Calcula la confianza de la placa detectada basada en el patrón.
        """
        if not plate:
            return 0.0

        # Verificar formato estándar boliviano (con o sin guión)
        if re.match(r'\d{4}-[A-Z]{3}', plate) or re.match(r'\d{4}[A-Z]{3}', plate):
            return 95.0
        elif re.match(r'\d{3}-[A-Z]{3}', plate) or re.match(r'\d{3}[A-Z]{3}', plate):
            return 90.0
        elif re.match(r'[A-Z]{3}-\d{3}', plate) or re.match(r'[A-Z]{3}\d{3}', plate):
            return 85.0
        else:
            return 60.0

    @staticmethod
    def process_vehicle_image(image_path):
        """
        Método principal para procesar una imagen de vehículo y extraer la placa.
        """
        try:
            print(f"[OCR DEBUG] Iniciando procesamiento de imagen: {image_path}")

            # Verificar que el archivo existe
            if not os.path.exists(image_path):
                print(f"[OCR DEBUG] Error: Archivo no encontrado: {image_path}")
                return {
                    'success': False,
                    'error': 'Archivo de imagen no encontrado',
                    'plate': None,
                    'confidence': 0.0
                }

            # Usar Google Vision para reconocimiento de placas
            if not GOOGLE_VISION_AVAILABLE:
                print("[OCR DEBUG] Error: Google Vision no está disponible")
                return {
                    'success': False,
                    'error': 'Servicio de reconocimiento no disponible. Google Vision no configurado.',
                    'plate': None,
                    'confidence': 0.0
                }

            print("[OCR DEBUG] Usando Google Vision para reconocimiento...")
            extracted_text, ocr_confidence = VehicleOCRService.extract_text_with_google_vision(image_path)

            if not extracted_text:
                print("[OCR DEBUG] Google Vision no pudo detectar placa")
                return {
                    'success': False,
                    'error': 'No se pudo detectar placa en la imagen',
                    'plate': None,
                    'confidence': 0.0
                }

            # Detectar placa en el texto extraído
            plate, plate_confidence = VehicleOCRService.detect_license_plate(extracted_text)
            print(f"[OCR DEBUG] Placa detectada: '{plate}', confianza: {plate_confidence}")

            if not plate:
                print(f"[OCR DEBUG] No se detectó placa boliviana válida en: '{extracted_text}'")
                return {
                    'success': False,
                    'error': 'No se detectó ninguna placa boliviana válida',
                    'plate': None,
                    'confidence': 0.0,
                    'extracted_text': extracted_text
                }

            # Calcular confianza final
            final_confidence = min(ocr_confidence, plate_confidence)

            return {
                'success': True,
                'plate': plate,
                'confidence': final_confidence,
                'extracted_text': extracted_text,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error procesando imagen: {str(e)}',
                'plate': None,
                'confidence': 0.0
            }