from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from typing import List, Optional, Dict, Any

from .models import (
    Infraccion, Cargo, TipoInfraccion, EstadoInfraccion, TipoCargo, EstadoCargo
)
from apps.properties.models import Propietario


class MultasService:
    """
    Servicio para gestionar la lógica de negocio de multas e infracciones
    """

    @staticmethod
    def registrar_infraccion(
        propietario_id: int,
        tipo_infraccion_id: int,
        descripcion: str,
        fecha_infraccion: datetime,
        reportado_por_id: Optional[int] = None,
        evidencia_url: Optional[str] = None,
        observaciones_admin: str = ""
    ) -> Infraccion:
        """
        Registra una nueva infracción
        """
        try:
            propietario = Propietario.objects.get(id=propietario_id)
        except Propietario.DoesNotExist:
            raise ValueError(f"Propietario con ID {propietario_id} no existe")

        # Verificar si el tipo de infracción existe y está activo
        try:
            tipo_infraccion = TipoInfraccion.objects.get(id=tipo_infraccion_id, es_activo=True)
        except TipoInfraccion.DoesNotExist:
            raise ValueError(f"Tipo de infracción con ID {tipo_infraccion_id} no existe o no está activo")

        with transaction.atomic():
            infraccion = Infraccion.objects.create(
                propietario=propietario,
                unidad=propietario.unidad,
                tipo_infraccion=tipo_infraccion,
                descripcion=descripcion,
                fecha_infraccion=fecha_infraccion,
                reportado_por_id=reportado_por_id,
                evidencia_url=evidencia_url,
                observaciones_admin=observaciones_admin,
                estado=EstadoInfraccion.REGISTRADA
            )

        return infraccion

    @staticmethod
    def confirmar_infraccion(infraccion_id: int, observaciones_admin: str = "") -> Infraccion:
        """
        Confirma una infracción y la marca para aplicación de multa
        """
        try:
            infraccion = Infraccion.objects.get(id=infraccion_id)
        except Infraccion.DoesNotExist:
            raise ValueError(f"Infracción con ID {infraccion_id} no existe")

        if infraccion.estado != EstadoInfraccion.REGISTRADA:
            raise ValueError(f"La infracción debe estar en estado 'REGISTRADA' para ser confirmada")

        infraccion.estado = EstadoInfraccion.CONFIRMADA
        if observaciones_admin:
            infraccion.observaciones_admin = observaciones_admin

        infraccion.save()
        return infraccion

    @staticmethod
    def rechazar_infraccion(infraccion_id: int, observaciones_admin: str) -> Infraccion:
        """
        Rechaza una infracción
        """
        try:
            infraccion = Infraccion.objects.get(id=infraccion_id)
        except Infraccion.DoesNotExist:
            raise ValueError(f"Infracción con ID {infraccion_id} no existe")

        if infraccion.estado not in [EstadoInfraccion.REGISTRADA, EstadoInfraccion.EN_REVISION]:
            raise ValueError(f"La infracción no puede ser rechazada en su estado actual")

        infraccion.estado = EstadoInfraccion.RECHAZADA
        infraccion.observaciones_admin = observaciones_admin
        infraccion.save()
        return infraccion

    @staticmethod
    def aplicar_multa(infraccion_id: int, monto_personalizado: Optional[Decimal] = None) -> Cargo:
        """
        Aplica multa automática basada en configuración o monto personalizado
        """
        try:
            infraccion = Infraccion.objects.get(id=infraccion_id)
        except Infraccion.DoesNotExist:
            raise ValueError(f"Infracción con ID {infraccion_id} no existe")

        if infraccion.estado != EstadoInfraccion.CONFIRMADA:
            raise ValueError("Solo se pueden aplicar multas a infracciones confirmadas")

        if infraccion.monto_multa:
            raise ValueError("Esta infracción ya tiene una multa aplicada")

        # Obtener configuración de multa o usar monto personalizado
        if monto_personalizado:
            monto_multa = monto_personalizado
            dias_pago = infraccion.tipo_infraccion.dias_para_pago  # Usar días del tipo de infracción
        else:
            # Usar montos del tipo de infracción
            monto_multa = infraccion.tipo_infraccion.monto_reincidencia if infraccion.es_reincidente else infraccion.tipo_infraccion.monto_base
            dias_pago = infraccion.tipo_infraccion.dias_para_pago

        with transaction.atomic():
            # Actualizar infracción
            infraccion.monto_multa = monto_multa
            infraccion.fecha_limite_pago = timezone.now().date() + timedelta(days=dias_pago)
            infraccion.estado = EstadoInfraccion.MULTA_APLICADA
            infraccion.save()

            # Crear cargo automáticamente
            cargo = Cargo.objects.create(
                propietario=infraccion.propietario,
                unidad=infraccion.unidad,
                concepto=f"Multa por {infraccion.tipo_infraccion.nombre}: {infraccion.descripcion[:100]}",
                tipo_cargo=TipoCargo.MULTA,
                monto=monto_multa,
                fecha_vencimiento=infraccion.fecha_limite_pago,
                infraccion=infraccion,
                observaciones=f"Multa generada automáticamente. Infracción ID: {infraccion.id}"
            )

        return cargo

    @staticmethod
    def procesar_pago_multa(cargo_id: int, monto_pago: Decimal) -> Dict[str, Any]:
        """
        Procesa el pago de una multa y actualiza estados
        """
        try:
            cargo = Cargo.objects.get(id=cargo_id, tipo_cargo=TipoCargo.MULTA)
        except Cargo.DoesNotExist:
            raise ValueError(f"Cargo de multa con ID {cargo_id} no existe")

        if cargo.estado == EstadoCargo.PAGADO:
            raise ValueError("Esta multa ya está completamente pagada")

        monto_total_adeudado = cargo.monto_total_con_intereses

        if monto_pago > monto_total_adeudado:
            raise ValueError(f"El monto del pago ({monto_pago}) excede la deuda total ({monto_total_adeudado})")

        with transaction.atomic():
            # Aplicar pago al cargo
            cargo.aplicar_pago(monto_pago)

            # Si se pagó completamente, actualizar infracción
            if cargo.estado == EstadoCargo.PAGADO and cargo.infraccion:
                cargo.infraccion.estado = EstadoInfraccion.PAGADA
                cargo.infraccion.save()

            # Generar cargo por intereses si había mora
            cargo_interes = None
            if cargo.interes_mora_calculado > Decimal('0.00'):
                cargo_interes = cargo.generar_cargo_interes_mora()

        return {
            'cargo': cargo,
            'cargo_interes': cargo_interes,
            'saldo_restante': cargo.saldo_pendiente,
            'pago_completo': cargo.estado == EstadoCargo.PAGADO
        }

    @staticmethod
    def obtener_infracciones_pendientes() -> List[Infraccion]:
        """
        Obtiene todas las infracciones pendientes de revisión
        """
        return Infraccion.objects.filter(
            estado__in=[EstadoInfraccion.REGISTRADA, EstadoInfraccion.EN_REVISION]
        ).select_related('propietario__user', 'unidad__bloque').order_by('-fecha_infraccion')

    @staticmethod
    def obtener_multas_vencidas() -> List[Cargo]:
        """
        Obtiene todas las multas vencidas
        """
        return Cargo.objects.filter(
            tipo_cargo=TipoCargo.MULTA,
            estado__in=[EstadoCargo.PENDIENTE, EstadoCargo.PARCIALMENTE_PAGADO],
            fecha_vencimiento__lt=timezone.now().date()
        ).select_related('propietario__user', 'unidad__bloque', 'infraccion')

    @staticmethod
    def calcular_estadisticas_infracciones(propietario_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calcula estadísticas de infracciones (por propietario o globales)
        """
        queryset = Infraccion.objects.all()
        if propietario_id:
            queryset = queryset.filter(propietario_id=propietario_id)

        estadisticas = {
            'total_infracciones': queryset.count(),
            'registradas': queryset.filter(estado=EstadoInfraccion.REGISTRADA).count(),
            'confirmadas': queryset.filter(estado=EstadoInfraccion.CONFIRMADA).count(),
            'rechazadas': queryset.filter(estado=EstadoInfraccion.RECHAZADA).count(),
            'multas_aplicadas': queryset.filter(estado=EstadoInfraccion.MULTA_APLICADA).count(),
            'multas_pagadas': queryset.filter(estado=EstadoInfraccion.PAGADA).count(),
            'por_tipo': {}
        }

        # Estadísticas por tipo de infracción
        tipos_infracciones = TipoInfraccion.objects.filter(es_activo=True)
        for tipo in tipos_infracciones:
            count = queryset.filter(tipo_infraccion=tipo).count()
            if count > 0:
                estadisticas['por_tipo'][tipo.nombre] = count

        return estadisticas

    @staticmethod
    def generar_intereses_mora_automaticos() -> List[Cargo]:
        """
        Genera automáticamente cargos por intereses de mora para cargos vencidos
        """
        cargos_vencidos = Cargo.objects.filter(
            estado__in=[EstadoCargo.PENDIENTE, EstadoCargo.PARCIALMENTE_PAGADO],
            fecha_vencimiento__lt=timezone.now().date() - timedelta(days=30)  # Al menos 30 días vencido
        ).exclude(tipo_cargo=TipoCargo.INTERES_MORA)

        cargos_interes_generados = []

        for cargo in cargos_vencidos:
            # Verificar si ya se generó interés para este cargo recientemente
            interes_existente = Cargo.objects.filter(
                tipo_cargo=TipoCargo.INTERES_MORA,
                observaciones__contains=f"Cargo original: {cargo.id}",
                fecha_emision__gte=timezone.now() - timedelta(days=35)
            ).exists()

            if not interes_existente:
                cargo_interes = cargo.generar_cargo_interes_mora()
                if cargo_interes:
                    cargos_interes_generados.append(cargo_interes)

        return cargos_interes_generados


class TipoInfraccionService:
    """
    Servicio para gestionar tipos de infracciones dinámicos
    """

    @staticmethod
    def crear_tipo_infraccion(
        codigo: str,
        nombre: str,
        monto_base: Decimal,
        monto_reincidencia: Decimal,
        dias_para_pago: int = 15,
        descripcion: str = "",
        orden: int = 0
    ) -> TipoInfraccion:
        """
        Crea un nuevo tipo de infracción
        """
        if TipoInfraccion.objects.filter(codigo=codigo).exists():
            raise ValueError(f"Ya existe un tipo de infracción con código '{codigo}'")

        return TipoInfraccion.objects.create(
            codigo=codigo,
            nombre=nombre,
            descripcion=descripcion,
            monto_base=monto_base,
            monto_reincidencia=monto_reincidencia,
            dias_para_pago=dias_para_pago,
            orden=orden,
            es_activo=True
        )

    @staticmethod
    def actualizar_tipo_infraccion(
        tipo_id: int,
        codigo: Optional[str] = None,
        nombre: Optional[str] = None,
        monto_base: Optional[Decimal] = None,
        monto_reincidencia: Optional[Decimal] = None,
        dias_para_pago: Optional[int] = None,
        descripcion: Optional[str] = None,
        orden: Optional[int] = None,
        es_activo: Optional[bool] = None
    ) -> TipoInfraccion:
        """
        Actualiza un tipo de infracción existente
        """
        try:
            tipo = TipoInfraccion.objects.get(id=tipo_id)
        except TipoInfraccion.DoesNotExist:
            raise ValueError(f"No existe tipo de infracción con ID '{tipo_id}'")

        if codigo is not None and codigo != tipo.codigo:
            if TipoInfraccion.objects.filter(codigo=codigo).exists():
                raise ValueError(f"Ya existe un tipo de infracción con código '{codigo}'")
            tipo.codigo = codigo
        if nombre is not None:
            tipo.nombre = nombre
        if monto_base is not None:
            tipo.monto_base = monto_base
        if monto_reincidencia is not None:
            tipo.monto_reincidencia = monto_reincidencia
        if dias_para_pago is not None:
            tipo.dias_para_pago = dias_para_pago
        if descripcion is not None:
            tipo.descripcion = descripcion
        if orden is not None:
            tipo.orden = orden
        if es_activo is not None:
            tipo.es_activo = es_activo

        tipo.save()
        return tipo

    @staticmethod
    def obtener_tipos_activos() -> List[TipoInfraccion]:
        """
        Obtiene todos los tipos de infracciones activos
        """
        return TipoInfraccion.objects.filter(es_activo=True).order_by('orden', 'nombre')

    @staticmethod
    def activar_tipo(tipo_id: int) -> TipoInfraccion:
        """
        Activa un tipo de infracción
        """
        try:
            tipo = TipoInfraccion.objects.get(id=tipo_id)
            tipo.es_activo = True
            tipo.save()
            return tipo
        except TipoInfraccion.DoesNotExist:
            raise ValueError(f"No existe tipo de infracción con ID '{tipo_id}'")

    @staticmethod
    def desactivar_tipo(tipo_id: int) -> TipoInfraccion:
        """
        Desactiva un tipo de infracción
        """
        try:
            tipo = TipoInfraccion.objects.get(id=tipo_id)
            tipo.es_activo = False
            tipo.save()
            return tipo
        except TipoInfraccion.DoesNotExist:
            raise ValueError(f"No existe tipo de infracción con ID '{tipo_id}'")