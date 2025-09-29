import logging
import boto3
from typing import List, Optional, Tuple, Dict, Any
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from ai_security.models import PersonProfile, FacialAccessLog
from botocore.exceptions import ClientError
import tempfile
import os

logger = logging.getLogger(__name__)


class AWSFacialRecognitionService:
    """
    Servicio para reconocimiento facial usando Amazon Rekognition.
    """

    def __init__(self):
        """Inicializar cliente de AWS Rekognition."""
        try:
            # Verificar que tenemos las credenciales necesarias
            if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
                # Si no están en settings, usar credenciales por defecto (perfil, variables de entorno, etc.)
                self.rekognition_client = boto3.client(
                    'rekognition',
                    region_name=settings.AWS_DEFAULT_REGION
                )
            else:
                self.rekognition_client = boto3.client(
                    'rekognition',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_DEFAULT_REGION
                )
            self.collection_id = settings.AWS_REKOGNITION_COLLECTION_ID
            self._ensure_collection_exists()
            logger.info(f"✅ AWS Rekognition inicializado correctamente. Collection: {self.collection_id}")
        except Exception as e:
            logger.error(f"❌ Error inicializando AWS Rekognition: {str(e)}")
            raise e

    def _ensure_collection_exists(self):
        """Asegurar que la collection de Rekognition existe."""
        try:
            # Intentar describir la collection
            self.rekognition_client.describe_collection(CollectionId=self.collection_id)
            logger.info(f"Collection '{self.collection_id}' ya existe")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # La collection no existe, crearla
                try:
                    self.rekognition_client.create_collection(CollectionId=self.collection_id)
                    logger.info(f"✅ Collection '{self.collection_id}' creada exitosamente")
                except ClientError as create_error:
                    logger.error(f"❌ Error creando collection: {create_error}")
                    raise create_error
            else:
                logger.error(f"❌ Error verificando collection: {e}")
                raise e

    def _read_image_bytes(self, image_path: str) -> bytes:
        """Leer imagen como bytes."""
        with open(image_path, 'rb') as image_file:
            return image_file.read()

    def index_face(self, image_path: str, external_image_id: str) -> Optional[str]:
        """
        Indexar una cara en la collection de AWS Rekognition.

        Args:
            image_path: Ruta de la imagen
            external_image_id: ID externo para asociar (ej: person_profile_123)

        Returns:
            Face ID de AWS Rekognition o None si falla
        """
        try:
            logger.info(f"🔍 Indexando cara en AWS Rekognition: {external_image_id}")

            # Leer imagen
            image_bytes = self._read_image_bytes(image_path)

            # Indexar cara en AWS Rekognition
            response = self.rekognition_client.index_faces(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                ExternalImageId=external_image_id,
                MaxFaces=1,
                QualityFilter='AUTO',
                DetectionAttributes=['ALL']
            )

            if response['FaceRecords']:
                face_id = response['FaceRecords'][0]['Face']['FaceId']
                confidence = response['FaceRecords'][0]['Face']['Confidence']
                logger.info(f"✅ Cara indexada exitosamente. FaceId: {face_id}, Confianza: {confidence:.2f}%")
                return face_id
            else:
                logger.warning(f"⚠️ No se detectó ninguna cara en la imagen: {image_path}")
                return None

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'InvalidParameterException':
                logger.warning(f"⚠️ Imagen no válida o sin rostros detectables: {image_path}")
            else:
                logger.error(f"❌ Error AWS indexando cara: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error indexando cara: {str(e)}")
            return None

    def search_faces_by_image(self, image_path: str, threshold: float = 80.0) -> Tuple[Optional[str], float]:
        """
        Buscar caras similares en la collection usando una imagen.

        Args:
            image_path: Ruta de la imagen a buscar
            threshold: Umbral mínimo de confianza (default: 80%)

        Returns:
            Tupla con (Face ID encontrado, confianza) o (None, 0.0)
        """
        try:
            logger.info(f"🔍 Buscando cara en collection AWS: {image_path}")

            # Leer imagen
            image_bytes = self._read_image_bytes(image_path)

            # Buscar caras similares
            response = self.rekognition_client.search_faces_by_image(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                FaceMatchThreshold=threshold,
                MaxFaces=1
            )

            if response['FaceMatches']:
                match = response['FaceMatches'][0]
                face_id = match['Face']['FaceId']
                confidence = match['Similarity']
                logger.info(f"✅ Cara encontrada. FaceId: {face_id}, Confianza: {confidence:.2f}%")
                return face_id, confidence
            else:
                logger.info(f"❌ No se encontraron coincidencias por encima del umbral {threshold}%")
                return None, 0.0

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'InvalidParameterException':
                logger.warning(f"⚠️ No se detectó rostro en la imagen: {image_path}")
            else:
                logger.error(f"❌ Error AWS buscando cara: {e}")
            return None, 0.0
        except Exception as e:
            logger.error(f"❌ Error buscando cara: {str(e)}")
            return None, 0.0

    def delete_face(self, face_id: str) -> bool:
        """
        Eliminar una cara de la collection.

        Args:
            face_id: ID de la cara en AWS Rekognition

        Returns:
            True si se eliminó exitosamente
        """
        try:
            logger.info(f"🗑️ Eliminando cara de AWS: {face_id}")

            self.rekognition_client.delete_faces(
                CollectionId=self.collection_id,
                FaceIds=[face_id]
            )

            logger.info(f"✅ Cara eliminada exitosamente: {face_id}")
            return True

        except ClientError as e:
            logger.error(f"❌ Error AWS eliminando cara: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error eliminando cara: {str(e)}")
            return False

    def register_new_person(self, image_path: str, name: str, person_type: str,
                           is_authorized: bool = False, user=None) -> Dict[str, Any]:
        """
        Registrar una nueva persona usando AWS Rekognition.

        Args:
            image_path: Ruta de la imagen
            name: Nombre de la persona
            person_type: Tipo de persona
            is_authorized: Si está autorizada
            user: Usuario asociado (opcional)

        Returns:
            Diccionario con resultado del registro
        """
        try:
            logger.info(f"👤 Registrando nueva persona: {name}")

            # Crear el perfil primero para obtener el ID
            person_profile = PersonProfile.objects.create(
                name=name,
                person_type=person_type,
                is_authorized=is_authorized,
                user=user
            )

            # Indexar cara en AWS Rekognition
            external_image_id = f"person_profile_{person_profile.id}"
            aws_face_id = self.index_face(image_path, external_image_id)

            if not aws_face_id:
                # Si falla la indexación, eliminar el perfil
                person_profile.delete()
                return {
                    'success': False,
                    'error': 'No se detectó ningún rostro válido en la imagen'
                }

            # Guardar el Face ID en el perfil
            person_profile.aws_face_id = aws_face_id
            person_profile.save()

            # Copiar imagen al storage del perfil
            with open(image_path, 'rb') as image_file:
                person_profile.photo.save(
                    f"person_{person_profile.id}.jpg",
                    ContentFile(image_file.read()),
                    save=True
                )

            logger.info(f"✅ Persona registrada exitosamente: {name} (FaceId: {aws_face_id})")
            return {
                'success': True,
                'person_profile': person_profile,
                'message': f'Persona {name} registrada exitosamente con AWS Rekognition'
            }

        except Exception as e:
            logger.error(f"❌ Error registrando nueva persona: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def identify_person(self, image_path: str, threshold: float = 80.0) -> Dict[str, Any]:
        """
        Identificar una persona usando AWS Rekognition.

        Args:
            image_path: Ruta de la imagen a analizar
            threshold: Umbral mínimo de confianza

        Returns:
            Diccionario con resultado de identificación
        """
        try:
            logger.info(f"🔍 Iniciando identificación con AWS Rekognition: {image_path}")

            # Buscar cara en la collection
            aws_face_id, confidence = self.search_faces_by_image(image_path, threshold)

            if not aws_face_id:
                logger.info("❌ Persona no reconocida por AWS Rekognition")
                return {
                    'success': True,
                    'person_profile': None,
                    'confidence': 0.0,
                    'access_granted': False,
                    'message': 'Persona no reconocida'
                }

            # Buscar perfil por Face ID
            try:
                person_profile = PersonProfile.objects.get(aws_face_id=aws_face_id, is_authorized=True)
                logger.info(f"✅ Persona identificada: {person_profile.name} (confianza: {confidence:.2f}%)")

                return {
                    'success': True,
                    'person_profile': person_profile,
                    'confidence': round(confidence, 2),
                    'access_granted': person_profile.is_authorized
                }

            except PersonProfile.DoesNotExist:
                logger.warning(f"⚠️ Face ID encontrado pero perfil no autorizado o no existe: {aws_face_id}")
                return {
                    'success': True,
                    'person_profile': None,
                    'confidence': round(confidence, 2),
                    'access_granted': False,
                    'message': 'Persona no autorizada'
                }

        except Exception as e:
            logger.error(f"❌ Error identificando persona: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'person_profile': None,
                'confidence': 0.0
            }

    def process_access_request(self, image_path: str, location: str = 'Entrada Principal',
                              threshold: float = 80.0) -> Dict[str, Any]:
        """
        Procesar solicitud completa de acceso facial con AWS Rekognition.

        Args:
            image_path: Ruta de la imagen
            location: Ubicación del acceso
            threshold: Umbral de confianza

        Returns:
            Diccionario con resultado completo
        """
        try:
            # Identificar persona
            identification_result = self.identify_person(image_path, threshold)

            if not identification_result['success']:
                return identification_result

            person_profile = identification_result.get('person_profile')
            confidence = identification_result.get('confidence', 0.0)
            access_granted = identification_result.get('access_granted', False)

            # Registrar intento de acceso
            access_log = self.log_access_attempt(
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
                'message': identification_result.get('message', 'Procesamiento completado con AWS Rekognition')
            }

        except Exception as e:
            logger.error(f"❌ Error procesando solicitud de acceso: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def log_access_attempt(self, image_path: str, person_profile: Optional[PersonProfile] = None,
                          confidence: float = 0.0, access_granted: bool = False,
                          location: str = 'Entrada Principal', detected_name: str = '') -> FacialAccessLog:
        """
        Registrar intento de acceso facial.

        Args:
            image_path: Ruta de la imagen del intento
            person_profile: Perfil de la persona identificada
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
            logger.error(f"❌ Error registrando log de acceso: {str(e)}")
            raise e

    def delete_person_profile(self, person_profile: PersonProfile) -> bool:
        """
        Eliminar perfil de persona incluyendo su Face ID en AWS.

        Args:
            person_profile: Perfil a eliminar

        Returns:
            True si se eliminó exitosamente
        """
        try:
            if person_profile.aws_face_id:
                # Eliminar de AWS Rekognition
                success = self.delete_face(person_profile.aws_face_id)
                if not success:
                    logger.warning(f"⚠️ No se pudo eliminar Face ID de AWS: {person_profile.aws_face_id}")

            # Eliminar perfil de la base de datos
            person_profile.delete()
            logger.info(f"✅ Perfil eliminado exitosamente: {person_profile.name}")
            return True

        except Exception as e:
            logger.error(f"❌ Error eliminando perfil: {str(e)}")
            return False