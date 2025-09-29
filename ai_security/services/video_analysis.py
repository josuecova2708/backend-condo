"""
Servicio para análisis de videos usando Amazon Rekognition.
Detecta actividades sospechosas, accidentes vehiculares y animales sueltos.
"""

import boto3
import json
import time
from django.conf import settings
from django.utils import timezone
from typing import Dict, List, Any, Optional
from ..models import AnalisisVideo, DeteccionActividad, TipoActividad


class VideoAnalysisService:
    """Servicio para análisis de videos con Amazon Rekognition"""

    def __init__(self):
        self.rekognition = boto3.client(
            'rekognition',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION
        )

        # Configuraciones de detección por categoría
        self.detection_configs = {
            'SOSPECHOSA': {
                'labels': ['Person', 'Gun', 'Weapon', 'Fight', 'Violence', 'Aggression'],
                'min_confidence': 70.0,
                'description': 'Actividades sospechosas: personas, armas, peleas'
            },
            'ACCIDENTE': {
                'labels': ['Car', 'Vehicle', 'Accident', 'Crash', 'Collision', 'Emergency'],
                'min_confidence': 75.0,
                'description': 'Accidentes vehiculares y emergencias'
            },
            'ANIMAL': {
                'labels': ['Dog', 'Cat', 'Pet', 'Animal', 'Stray'],
                'min_confidence': 80.0,
                'description': 'Animales sueltos en el área'
            }
        }

    def iniciar_analisis(self, camera_id: str, video_name: str, video_url: str, usuario) -> AnalisisVideo:
        """
        Inicia el análisis de un video con Amazon Rekognition
        """
        try:
            # Crear registro de análisis
            analisis = AnalisisVideo.objects.create(
                camera_id=camera_id,
                video_name=video_name,
                video_url=video_url,
                usuario=usuario,
                estado='PENDIENTE'
            )

            # Extraer bucket y key del video_url
            bucket_name = settings.AWS_S3_BUCKET_NAME
            video_key = f"{camera_id}/{video_name}"

            # Iniciar análisis de etiquetas con Rekognition
            try:
                response = self.rekognition.start_label_detection(
                    Video={
                        'S3Object': {
                            'Bucket': bucket_name,
                            'Name': video_key
                        }
                    },
                    MinConfidence=60.0,  # Confianza mínima para todas las detecciones
                    Features=['GENERAL_LABELS'],
                    JobTag=f"analysis_{analisis.id}"
                )

                # Guardar job ID y actualizar estado
                analisis.job_id = response['JobId']
                analisis.estado = 'PROCESANDO'
                analisis.save()

                print(f"Análisis iniciado - Job ID: {response['JobId']}")
                return analisis

            except Exception as rekognition_error:
                analisis.estado = 'ERROR'
                analisis.error_mensaje = f"Error en Rekognition: {str(rekognition_error)}"
                analisis.save()
                raise

        except Exception as e:
            print(f"Error iniciando análisis: {e}")
            raise

    def verificar_estado_analisis(self, analisis: AnalisisVideo) -> bool:
        """
        Verifica el estado del análisis en Rekognition y procesa resultados si está completo
        """
        if not analisis.job_id or analisis.estado != 'PROCESANDO':
            return False

        try:
            response = self.rekognition.get_label_detection(JobId=analisis.job_id)
            job_status = response['JobStatus']

            if job_status == 'SUCCEEDED':
                # Procesar resultados
                self._procesar_resultados(analisis, response)
                analisis.estado = 'COMPLETADO'
                analisis.completado_at = timezone.now()
                analisis.save()
                return True

            elif job_status == 'FAILED':
                analisis.estado = 'ERROR'
                analisis.error_mensaje = response.get('StatusMessage', 'Análisis falló en Rekognition')
                analisis.save()
                return False

            # Aún procesando
            return False

        except Exception as e:
            analisis.estado = 'ERROR'
            analisis.error_mensaje = f"Error verificando estado: {str(e)}"
            analisis.save()
            return False

    def _procesar_resultados(self, analisis: AnalisisVideo, rekognition_response: Dict) -> None:
        """
        Procesa los resultados de Rekognition y crea detecciones de actividades
        """
        labels = rekognition_response.get('Labels', [])
        detecciones_creadas = 0
        confianzas = []

        print(f"Procesando {len(labels)} etiquetas detectadas")

        # Agrupar labels por timestamp para crear detecciones
        detecciones_por_timestamp = {}

        for label_data in labels:
            label_name = label_data['Label']['Name']
            confidence = label_data['Label']['Confidence']
            timestamp = label_data['Timestamp'] / 1000.0  # Convertir de ms a segundos

            # Verificar qué categorías coinciden con esta etiqueta
            categorias_detectadas = self._clasificar_etiqueta(label_name, confidence)

            for categoria in categorias_detectadas:
                # Crear o actualizar detección para esta categoría y timestamp
                key = f"{categoria}_{int(timestamp)}"
                if key not in detecciones_por_timestamp:
                    detecciones_por_timestamp[key] = {
                        'categoria': categoria,
                        'timestamp_inicio': timestamp,
                        'timestamp_fin': timestamp,
                        'objetos': [],
                        'confianzas': [],
                        'bounding_boxes': []
                    }

                detecciones_por_timestamp[key]['timestamp_fin'] = max(
                    detecciones_por_timestamp[key]['timestamp_fin'],
                    timestamp
                )
                detecciones_por_timestamp[key]['objetos'].append(label_name)
                detecciones_por_timestamp[key]['confianzas'].append(confidence)

        # Crear detecciones en la base de datos
        for deteccion_data in detecciones_por_timestamp.values():
            categoria = deteccion_data['categoria']

            # Obtener o crear tipo de actividad
            tipo_actividad, created = TipoActividad.objects.get_or_create(
                categoria=categoria,
                nombre=self.detection_configs[categoria]['description'],
                defaults={
                    'descripcion': self.detection_configs[categoria]['description'],
                    'palabras_clave': ','.join(self.detection_configs[categoria]['labels'])
                }
            )

            # Calcular confianza promedio
            confianza_promedio = sum(deteccion_data['confianzas']) / len(deteccion_data['confianzas'])

            if confianza_promedio >= self.detection_configs[categoria]['min_confidence']:
                # Crear detección
                deteccion = DeteccionActividad.objects.create(
                    analisis=analisis,
                    tipo_actividad=tipo_actividad,
                    timestamp_inicio=deteccion_data['timestamp_inicio'],
                    timestamp_fin=deteccion_data['timestamp_fin'],
                    confianza=confianza_promedio,
                    objetos_detectados=list(set(deteccion_data['objetos'])),  # Eliminar duplicados
                    bounding_boxes=deteccion_data['bounding_boxes']
                )

                detecciones_creadas += 1
                confianzas.append(confianza_promedio)

                print(f"Detección creada: {tipo_actividad.nombre} - {confianza_promedio:.1f}% confianza")

                # Generar aviso automático para detecciones de alta confianza
                if confianza_promedio >= 80.0:  # Solo para detecciones muy confiables
                    try:
                        aviso_id = self.generar_aviso_actividad(deteccion)
                        if aviso_id:
                            print(f"Aviso automático generado para detección {deteccion.id}")
                    except Exception as e:
                        print(f"Error generando aviso automático: {e}")

        # Actualizar estadísticas del análisis
        analisis.actividades_detectadas = detecciones_creadas
        if confianzas:
            analisis.confianza_promedio = sum(confianzas) / len(confianzas)
        analisis.save()

        print(f"Análisis completado: {detecciones_creadas} actividades detectadas")

    def _clasificar_etiqueta(self, label_name: str, confidence: float) -> List[str]:
        """
        Clasifica una etiqueta en las categorías de actividades que detectamos
        """
        categorias = []

        for categoria, config in self.detection_configs.items():
            # Verificar si la etiqueta coincide con alguna de las palabras clave
            for keyword in config['labels']:
                if keyword.lower() in label_name.lower():
                    if confidence >= config['min_confidence']:
                        categorias.append(categoria)
                    break

        return categorias

    def obtener_analisis_pendientes(self) -> List[AnalisisVideo]:
        """
        Obtiene análisis que están en estado PROCESANDO para verificar su estado
        """
        return AnalisisVideo.objects.filter(estado='PROCESANDO')

    def generar_aviso_actividad(self, deteccion: DeteccionActividad) -> Optional[int]:
        """
        Genera un aviso/comunicado automático para una detección de actividad
        """
        try:
            from apps.communications.models import AvisoComunicado
            from apps.users.models import User

            # Obtener admin del sistema para crear el aviso
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                print("No se encontró usuario administrador para crear aviso")
                return None

            # Crear título y contenido del aviso
            categoria_display = deteccion.tipo_actividad.get_categoria_display()

            titulo = f"🚨 ALERTA: {categoria_display} Detectada"

            contenido = f"""
ALERTA AUTOMÁTICA DE SEGURIDAD

📍 Ubicación: {deteccion.analisis.camera_id.upper()}
📹 Video: {deteccion.analisis.video_name}
⏰ Tiempo: {deteccion.timestamp_inicio:.1f}s - {deteccion.timestamp_fin:.1f}s
🎯 Confianza: {deteccion.confianza:.1f}%

🔍 Objetos detectados:
{', '.join(deteccion.objetos_detectados)}

📋 Descripción:
{deteccion.tipo_actividad.descripcion}

⚠️ Se recomienda revisar inmediatamente las grabaciones de seguridad.

---
Este aviso fue generado automáticamente por el sistema de IA de seguridad.
            """.strip()

            # Crear aviso
            aviso = AvisoComunicado.objects.create(
                titulo=titulo,
                contenido=contenido,
                usuario=admin_user,
                prioridad='ALTA',
                tipo='SEGURIDAD'
            )

            # Marcar que se generó el aviso
            deteccion.aviso_generado = True
            deteccion.aviso_id = aviso.id
            deteccion.save()

            print(f"Aviso generado: {titulo}")
            return aviso.id

        except Exception as e:
            print(f"Error generando aviso: {e}")
            return None