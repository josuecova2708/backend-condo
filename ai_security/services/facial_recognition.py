import json
import logging
from typing import List, Optional, Tuple, Dict, Any
import cv2
import numpy as np
from PIL import Image
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from ai_security.models import PersonProfile, FacialAccessLog

logger = logging.getLogger(__name__)


class FacialRecognitionService:
    """
    Servicio para reconocimiento facial usando OpenCV + NumPy.
    """

    # Inicializar detectores de OpenCV
    _face_cascade = None
    _eye_cascade = None

    @classmethod
    def _get_face_cascade(cls):
        """Obtener clasificador Haar para detección facial."""
        if cls._face_cascade is None:
            cls._face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        return cls._face_cascade

    @classmethod
    def _get_eye_cascade(cls):
        """Obtener clasificador Haar para detección de ojos."""
        if cls._eye_cascade is None:
            cls._eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        return cls._eye_cascade

    @staticmethod
    def encode_face(image_path: str) -> Optional[List[float]]:
        """
        Genera el encoding facial de una imagen usando OpenCV.

        Args:
            image_path: Ruta de la imagen

        Returns:
            Lista con el encoding facial o None si no se detecta rostro
        """
        try:
            # Cargar imagen con OpenCV
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"No se pudo cargar la imagen: {image_path}")
                return None

            # Convertir a escala de grises
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Detectar rostros usando clasificador Haar con parámetros más permisivos
            face_cascade = FacialRecognitionService._get_face_cascade()
            faces = face_cascade.detectMultiScale(gray, 1.1, 3, minSize=(30, 30))

            if len(faces) == 0:
                logger.warning(f"No se detectó ningún rostro en la imagen: {image_path}")
                return None

            if len(faces) > 1:
                logger.warning(f"Se detectaron múltiples rostros en la imagen: {image_path}. Usando el más grande.")
                # Seleccionar el rostro más grande
                faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)

            # Tomar el primer/mayor rostro detectado
            (x, y, w, h) = faces[0]

            # Agregar padding para incluir más contexto facial
            padding = int(min(w, h) * 0.1)
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(gray.shape[1] - x, w + 2*padding)
            h = min(gray.shape[0] - y, h + 2*padding)

            face_roi = gray[y:y+h, x:x+w]

            # PREPROCESADO UNIFICADO Y MEJORADO
            # 1. Redimensionar a tamaño estándar para consistencia
            face_roi = cv2.resize(face_roi, (100, 100))

            # 2. Normalización de iluminación usando CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            face_roi = clahe.apply(face_roi)

            # 3. Suavizado para reducir ruido
            face_roi = cv2.GaussianBlur(face_roi, (3, 3), 0)

            # GENERACIÓN DE CARACTERÍSTICAS ROBUSTAS

            # 1. Histograma normalizado (más suave, menos sensible a iluminación)
            hist = cv2.calcHist([face_roi], [0], None, [32], [0, 256])  # Menos bins para más robustez
            hist_features = hist.flatten()
            hist_features = hist_features / (np.sum(hist_features) + 1e-7)  # Normalización L1

            # 2. Momentos de Hu (invariantes geométricos)
            moments = cv2.moments(face_roi)
            hu_moments = cv2.HuMoments(moments).flatten()
            # Log transform para manejar valores grandes
            hu_moments = np.sign(hu_moments) * np.log10(np.abs(hu_moments) + 1e-7)

            # 3. Características de textura LBP-like simplificadas
            # Dividir imagen en regiones y calcular estadísticas locales
            regions = []
            h, w = face_roi.shape
            step_h, step_w = h//4, w//4

            for i in range(0, h-step_h, step_h):
                for j in range(0, w-step_w, step_w):
                    region = face_roi[i:i+step_h, j:j+step_w]
                    if region.size > 0:
                        regions.extend([
                            np.mean(region),
                            np.std(region)
                        ])

            # Limitar el número de características de regiones
            regions = regions[:20]  # Máximo 20 características

            # 4. Características de bordes más robustas
            # Usar Canny para detectar bordes fuertes
            edges = cv2.Canny(face_roi, 50, 150)
            edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])

            # Orientaciones de gradientes
            grad_x = cv2.Sobel(face_roi, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(face_roi, cv2.CV_64F, 0, 1, ksize=3)
            grad_orientation = np.arctan2(grad_y, grad_x)

            # Histograma de orientaciones (simplificado)
            orientation_hist, _ = np.histogram(grad_orientation.flatten(), bins=8, range=(-np.pi, np.pi))
            orientation_hist = orientation_hist / (np.sum(orientation_hist) + 1e-7)

            # Combinar todas las características de manera robusta
            all_features = []

            # Agregar características con pesos balanceados
            all_features.extend(hist_features * 10)  # Histograma con peso
            all_features.extend(hu_moments)  # Momentos Hu
            all_features.extend(regions)  # Características regionales
            all_features.append(edge_density * 100)  # Densidad de bordes
            all_features.extend(orientation_hist * 10)  # Histograma de orientaciones

            # Convertir a numpy y normalizar
            encoding = np.array(all_features)

            # Normalización robusta (Z-score clipping)
            encoding = np.clip(encoding, -3, 3)  # Clipear outliers

            # Normalización L2 final
            norm = np.linalg.norm(encoding)
            if norm > 0:
                encoding = encoding / norm

            return encoding.tolist()

        except Exception as e:
            logger.error(f"Error al procesar imagen {image_path}: {str(e)}")
            return None

    @staticmethod
    def compare_faces(known_encodings: List[List[float]], unknown_encoding: List[float], tolerance: float = 2.0) -> Tuple[List[bool], List[float]]:
        """
        Compara un encoding desconocido con encodings conocidos usando distancia euclidiana.

        Args:
            known_encodings: Lista de encodings conocidos
            unknown_encoding: Encoding a comparar
            tolerance: Tolerancia para considerar una coincidencia (default: 2.0 para OpenCV - muy permisivo)

        Returns:
            Tupla con (lista de coincidencias booleanas, lista de distancias)
        """
        try:
            if not known_encodings or not unknown_encoding:
                return [], []

            # Convertir a numpy arrays
            unknown_encoding_np = np.array(unknown_encoding)

            matches = []
            distances = []

            for known_encoding in known_encodings:
                known_encoding_np = np.array(known_encoding)

                # Verificar que los encodings tengan la misma dimensión
                if len(known_encoding_np) != len(unknown_encoding_np):
                    logger.warning(f"Dimensiones de encoding no coinciden: {len(known_encoding_np)} vs {len(unknown_encoding_np)}")
                    distances.append(float('inf'))
                    matches.append(False)
                    continue

                # Calcular distancia euclidiana normalizada
                distance = np.linalg.norm(known_encoding_np - unknown_encoding_np)

                # Normalizar la distancia por la dimensión del vector
                normalized_distance = distance / np.sqrt(len(unknown_encoding_np))

                distances.append(float(normalized_distance))
                matches.append(normalized_distance <= tolerance)

            return matches, distances

        except Exception as e:
            logger.error(f"Error al comparar encodings: {str(e)}")
            return [], []

    @staticmethod
    def identify_person(image_path: str) -> Dict[str, Any]:
        """
        Identifica una persona en una imagen comparando con la base de datos.

        Args:
            image_path: Ruta de la imagen a analizar

        Returns:
            Diccionario con resultado de identificación
        """
        try:
            logger.info(f"🔍 Iniciando identificación facial para imagen: {image_path}")

            # Generar encoding de la imagen desconocida
            unknown_encoding = FacialRecognitionService.encode_face(image_path)

            if not unknown_encoding:
                logger.warning("❌ No se detectó ningún rostro en la imagen")
                return {
                    'success': False,
                    'error': 'No se detectó ningún rostro en la imagen',
                    'person_profile': None,
                    'confidence': 0.0
                }

            logger.info(f"✅ Encoding generado exitosamente. Dimensión: {len(unknown_encoding)}")

            # Obtener todos los perfiles de personas
            person_profiles = PersonProfile.objects.filter(is_authorized=True)
            logger.info(f"📊 Perfiles autorizados encontrados: {person_profiles.count()}")

            if not person_profiles.exists():
                logger.warning("⚠️ No hay perfiles registrados para comparar")
                return {
                    'success': True,
                    'person_profile': None,
                    'confidence': 0.0,
                    'message': 'No hay perfiles registrados para comparar'
                }

            # Preparar encodings conocidos
            known_encodings = []
            profile_map = {}

            for profile in person_profiles:
                try:
                    encoding = json.loads(profile.face_encoding)
                    known_encodings.append(encoding)
                    profile_map[len(known_encodings) - 1] = profile
                    logger.debug(f"✅ Encoding cargado para {profile.name} (ID: {profile.id})")
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"❌ Error al cargar encoding del perfil {profile.id} ({profile.name}): {str(e)}")
                    continue

            logger.info(f"📋 Encodings válidos cargados: {len(known_encodings)}")

            if not known_encodings:
                logger.warning("⚠️ No hay encodings válidos para comparar")
                return {
                    'success': True,
                    'person_profile': None,
                    'confidence': 0.0,
                    'message': 'No hay encodings válidos para comparar'
                }

            # Comparar con encodings conocidos
            matches, distances = FacialRecognitionService.compare_faces(known_encodings, unknown_encoding)
            logger.info(f"🔄 Comparación completada. Matches: {sum(matches)}/{len(matches)}")

            # Encontrar la mejor coincidencia
            best_match_index = None
            best_confidence = 0.0

            for i, (match, distance) in enumerate(zip(matches, distances)):
                profile = profile_map[i]
                confidence = max(0, (1 - distance) * 100)  # Convertir distancia a porcentaje de confianza

                logger.info(f"👤 {profile.name}: distancia={distance:.4f}, confianza={confidence:.2f}%, match={match}")

                if match and confidence > best_confidence:
                    best_confidence = confidence
                    best_match_index = i

            if best_match_index is not None:
                matched_profile = profile_map[best_match_index]
                logger.info(f"🎯 Mejor coincidencia: {matched_profile.name} (confianza: {best_confidence:.2f}%)")
                return {
                    'success': True,
                    'person_profile': matched_profile,
                    'confidence': round(best_confidence, 2),
                    'access_granted': matched_profile.is_authorized
                }
            else:
                logger.info(f"❌ Persona no reconocida. Mejor confianza: {max([max(0, (1 - d) * 100) for d in distances], default=0):.2f}%")
                return {
                    'success': True,
                    'person_profile': None,
                    'confidence': 0.0,
                    'access_granted': False,
                    'message': 'Persona no reconocida'
                }

        except Exception as e:
            logger.error(f"Error al identificar persona: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'person_profile': None,
                'confidence': 0.0
            }

    @staticmethod
    def register_new_person(image_path: str, name: str, person_type: str, is_authorized: bool = False, user=None) -> Dict[str, Any]:
        """
        Registra una nueva persona en el sistema.

        Args:
            image_path: Ruta de la imagen
            name: Nombre de la persona
            person_type: Tipo de persona (resident, visitor, employee, delivery, unknown)
            is_authorized: Si la persona está autorizada
            user: Usuario asociado (opcional)

        Returns:
            Diccionario con resultado del registro
        """
        try:
            # Generar encoding facial
            face_encoding = FacialRecognitionService.encode_face(image_path)

            if not face_encoding:
                return {
                    'success': False,
                    'error': 'No se detectó ningún rostro en la imagen'
                }

            # Verificar si ya existe una persona similar
            existing_profiles = PersonProfile.objects.all()

            if existing_profiles.exists():
                known_encodings = []
                for profile in existing_profiles:
                    try:
                        encoding = json.loads(profile.face_encoding)
                        known_encodings.append(encoding)
                    except (json.JSONDecodeError, TypeError):
                        continue

                if known_encodings:
                    matches, distances = FacialRecognitionService.compare_faces(known_encodings, face_encoding, tolerance=0.6)

                    for i, (match, distance) in enumerate(zip(matches, distances)):
                        if match:
                            confidence = max(0, (1 - distance) * 100)
                            if confidence > 70:  # Alta similitud (ajustado para OpenCV)
                                return {
                                    'success': False,
                                    'error': f'Ya existe una persona muy similar registrada (confianza: {confidence:.1f}%)'
                                }

            # Crear nuevo perfil
            person_profile = PersonProfile.objects.create(
                name=name,
                person_type=person_type,
                face_encoding=json.dumps(face_encoding),
                is_authorized=is_authorized,
                user=user
            )

            # Copiar imagen al storage del perfil
            with open(image_path, 'rb') as image_file:
                person_profile.photo.save(
                    f"person_{person_profile.id}.jpg",
                    ContentFile(image_file.read()),
                    save=True
                )

            return {
                'success': True,
                'person_profile': person_profile,
                'message': f'Persona {name} registrada exitosamente'
            }

        except Exception as e:
            logger.error(f"Error al registrar nueva persona: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def log_access_attempt(image_path: str, person_profile: Optional[PersonProfile] = None,
                          confidence: float = 0.0, access_granted: bool = False,
                          location: str = 'Entrada Principal', detected_name: str = '') -> FacialAccessLog:
        """
        Registra un intento de acceso facial.

        Args:
            image_path: Ruta de la imagen del intento
            person_profile: Perfil de la persona identificada (opcional)
            confidence: Confianza de la identificación
            access_granted: Si se concedió el acceso
            location: Ubicación del acceso
            detected_name: Nombre detectado

        Returns:
            Instancia de FacialAccessLog creada
        """
        try:
            # Crear log de acceso
            access_log = FacialAccessLog.objects.create(
                person_profile=person_profile,
                confidence_score=confidence,
                access_granted=access_granted,
                location=location,
                detected_name=detected_name or (person_profile.name if person_profile else 'Desconocido')
            )

            # Guardar imagen del intento
            with open(image_path, 'rb') as image_file:
                access_log.photo.save(
                    f"access_attempt_{access_log.id}.jpg",
                    ContentFile(image_file.read()),
                    save=True
                )

            return access_log

        except Exception as e:
            logger.error(f"Error al registrar log de acceso: {str(e)}")
            raise e

    @staticmethod
    def process_access_request(image_path: str, location: str = 'Entrada Principal') -> Dict[str, Any]:
        """
        Procesa una solicitud completa de acceso facial.

        Args:
            image_path: Ruta de la imagen
            location: Ubicación del acceso

        Returns:
            Diccionario con resultado completo del procesamiento
        """
        try:
            # Identificar persona
            identification_result = FacialRecognitionService.identify_person(image_path)

            if not identification_result['success']:
                return identification_result

            person_profile = identification_result.get('person_profile')
            confidence = identification_result.get('confidence', 0.0)
            access_granted = identification_result.get('access_granted', False)

            # Registrar intento de acceso
            access_log = FacialRecognitionService.log_access_attempt(
                image_path=image_path,
                person_profile=person_profile,
                confidence=confidence,
                access_granted=access_granted,
                location=location,
                detected_name=person_profile.name if person_profile else 'Desconocido'
            )

            return {
                'success': True,
                'person_profile': person_profile,
                'confidence': confidence,
                'access_granted': access_granted,
                'access_log': access_log,
                'message': identification_result.get('message', 'Procesamiento completado')
            }

        except Exception as e:
            logger.error(f"Error al procesar solicitud de acceso: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }