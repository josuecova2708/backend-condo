from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from typing import List, Optional, Dict, Any

from .models import (
    Infraccion, Cargo, ConfiguracionMultas,
    TipoInfraccion, EstadoInfraccion, TipoCargo, EstadoCargo
)
from apps.properties.models import Propietario


class MultasService:
    """
    Servicio para gestionar la lógica de negocio de multas e infracciones
    """

    @staticmethod
    def registrar_infraccion(
        propietario_id: int,
        tipo_infraccion: str,
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

        # Verificar si el tipo de infracción es válido
        if tipo_infraccion not in [choice[0] for choice in TipoInfraccion.choices]:
            raise ValueError(f"Tipo de infracción '{tipo_infraccion}' no es válido")

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
            dias_pago = 15  # Default
        else:
            try:
                config = ConfiguracionMultas.objects.get(
                    tipo_infraccion=infraccion.tipo_infraccion,
                    es_activa=True
                )
                monto_multa = config.monto_reincidencia if infraccion.es_reincidente else config.monto_base
                dias_pago = config.dias_para_pago
            except ConfiguracionMultas.DoesNotExist:
                raise ValueError(f"No existe configuración activa para el tipo de infracción '{infraccion.tipo_infraccion}'")

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
                concepto=f"Multa por {infraccion.get_tipo_infraccion_display()}: {infraccion.descripcion[:100]}",
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
        for tipo_choice in TipoInfraccion.choices:
            tipo_code = tipo_choice[0]
            tipo_label = tipo_choice[1]
            count = queryset.filter(tipo_infraccion=tipo_code).count()
            if count > 0:
                estadisticas['por_tipo'][tipo_label] = count

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


class ConfiguracionMultasService:
    """
    Servicio para gestionar configuraciones de multas
    """

    @staticmethod
    def crear_configuracion(
        tipo_infraccion: str,
        monto_base: Decimal,
        monto_reincidencia: Decimal,
        dias_para_pago: int = 15,
        descripcion: str = ""
    ) -> ConfiguracionMultas:
        """
        Crea una nueva configuración de multa
        """
        if tipo_infraccion not in [choice[0] for choice in TipoInfraccion.choices]:
            raise ValueError(f"Tipo de infracción '{tipo_infraccion}' no es válido")

        if ConfiguracionMultas.objects.filter(tipo_infraccion=tipo_infraccion).exists():
            raise ValueError(f"Ya existe una configuración para el tipo '{tipo_infraccion}'")

        return ConfiguracionMultas.objects.create(
            tipo_infraccion=tipo_infraccion,
            monto_base=monto_base,
            monto_reincidencia=monto_reincidencia,
            dias_para_pago=dias_para_pago,
            descripcion=descripcion
        )

    @staticmethod
    def actualizar_configuracion(
        tipo_infraccion: str,
        monto_base: Optional[Decimal] = None,
        monto_reincidencia: Optional[Decimal] = None,
        dias_para_pago: Optional[int] = None,
        descripcion: Optional[str] = None,
        es_activa: Optional[bool] = None
    ) -> ConfiguracionMultas:
        """
        Actualiza una configuración existente
        """
        try:
            config = ConfiguracionMultas.objects.get(tipo_infraccion=tipo_infraccion)
        except ConfiguracionMultas.DoesNotExist:
            raise ValueError(f"No existe configuración para el tipo '{tipo_infraccion}'")

        if monto_base is not None:
            config.monto_base = monto_base
        if monto_reincidencia is not None:
            config.monto_reincidencia = monto_reincidencia
        if dias_para_pago is not None:
            config.dias_para_pago = dias_para_pago
        if descripcion is not None:
            config.descripcion = descripcion
        if es_activa is not None:
            config.es_activa = es_activa

        config.save()
        return config

    @staticmethod
    def obtener_configuraciones_activas() -> List[ConfiguracionMultas]:
        """
        Obtiene todas las configuraciones activas
        """
        return ConfiguracionMultas.objects.filter(es_activa=True).order_by('tipo_infraccion')