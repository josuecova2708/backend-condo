from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import random

from finances.models import (
    Infraccion, Cargo, ConfiguracionMultas,
    TipoInfraccion, EstadoInfraccion, TipoCargo, EstadoCargo
)
from apps.properties.models import Propietario, UnidadHabitacional
from apps.users.models import User
from apps.core.models import Condominio, Bloque


class Command(BaseCommand):
    help = 'Cargar datos de ejemplo para testear el sistema de multas CU11'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Limpiar datos existentes antes de cargar nuevos',
        )

    def handle(self, *args, **options):
        if options['clean']:
            self.stdout.write('Limpiando datos existentes...')
            Cargo.objects.all().delete()
            Infraccion.objects.all().delete()
            ConfiguracionMultas.objects.all().delete()

        self.stdout.write('Creando configuraciones de multas...')
        self.create_configuraciones_multas()

        self.stdout.write('Verificando datos básicos del condominio...')
        self.ensure_basic_data()

        self.stdout.write('Creando infracciones de ejemplo...')
        self.create_sample_infracciones()

        self.stdout.write('Creando cargos de ejemplo...')
        self.create_sample_cargos()

        self.stdout.write(
            self.style.SUCCESS('Datos de ejemplo cargados exitosamente!')
        )
        self.show_summary()

    def create_configuraciones_multas(self):
        """Crear configuraciones para todos los tipos de infracciones"""
        configuraciones = [
            {
                'tipo_infraccion': TipoInfraccion.RUIDO_EXCESIVO,
                'monto_base': Decimal('150.00'),
                'monto_reincidencia': Decimal('300.00'),
                'dias_para_pago': 15,
                'descripcion': 'Multa por ruido excesivo fuera de horarios permitidos'
            },
            {
                'tipo_infraccion': TipoInfraccion.USO_INADECUADO_AREAS,
                'monto_base': Decimal('200.00'),
                'monto_reincidencia': Decimal('400.00'),
                'dias_para_pago': 10,
                'descripcion': 'Uso inadecuado de áreas comunes del condominio'
            },
            {
                'tipo_infraccion': TipoInfraccion.MASCOTA_SIN_CORREA,
                'monto_base': Decimal('100.00'),
                'monto_reincidencia': Decimal('200.00'),
                'dias_para_pago': 20,
                'descripcion': 'Mascota en áreas comunes sin correa'
            },
            {
                'tipo_infraccion': TipoInfraccion.BASURA_HORARIO,
                'monto_base': Decimal('80.00'),
                'monto_reincidencia': Decimal('160.00'),
                'dias_para_pago': 15,
                'descripcion': 'Sacar basura fuera de horarios establecidos'
            },
            {
                'tipo_infraccion': TipoInfraccion.PARQUEADERO_INCORRECTO,
                'monto_base': Decimal('120.00'),
                'monto_reincidencia': Decimal('240.00'),
                'dias_para_pago': 10,
                'descripcion': 'Parquear en espacios no autorizados'
            },
        ]

        for config_data in configuraciones:
            config, created = ConfiguracionMultas.objects.get_or_create(
                tipo_infraccion=config_data['tipo_infraccion'],
                defaults=config_data
            )
            if created:
                self.stdout.write(f'  * Configuracion creada: {config.get_tipo_infraccion_display()}')

    def ensure_basic_data(self):
        """Asegurar que existan datos básicos del condominio"""
        # Verificar que exista al menos un condominio
        condominio = Condominio.objects.first()
        if not condominio:
            condominio = Condominio.objects.create(
                nombre="Condominio Las Flores",
                direccion="Av. Ejemplo 123, Santa Cruz, Bolivia",
                telefono="+591 3 123-4567",
                email="admin@lasflores.com",
                nit="1234567890"
            )
            self.stdout.write(f'  ✓ Condominio creado: {condominio.nombre}')

        # Verificar que exista al menos un bloque
        bloque = Bloque.objects.first()
        if not bloque:
            bloque = Bloque.objects.create(
                condominio=condominio,
                nombre="Bloque A",
                descripcion="Bloque principal del condominio",
                numero_pisos=5
            )
            self.stdout.write(f'  ✓ Bloque creado: {bloque.nombre}')

        # Verificar que existan unidades habitacionales
        unidades = UnidadHabitacional.objects.count()
        if unidades < 3:
            for i in range(1, 6):
                unidad, created = UnidadHabitacional.objects.get_or_create(
                    bloque=bloque,
                    numero=f"A{i:02d}",
                    defaults={
                        'area_m2': Decimal('85.50'),
                        'num_habitaciones': 3,
                        'num_banos': 2,
                        'tiene_parqueadero': True
                    }
                )
                if created:
                    self.stdout.write(f'  ✓ Unidad creada: {unidad}')

        # Verificar que existan propietarios
        propietarios = Propietario.objects.count()
        if propietarios < 3:
            # Crear usuarios propietarios de ejemplo
            usuarios_data = [
                {'username': 'juan.perez', 'first_name': 'Juan', 'last_name': 'Pérez', 'email': 'juan@ejemplo.com'},
                {'username': 'maria.garcia', 'first_name': 'María', 'last_name': 'García', 'email': 'maria@ejemplo.com'},
                {'username': 'carlos.lopez', 'first_name': 'Carlos', 'last_name': 'López', 'email': 'carlos@ejemplo.com'},
            ]

            unidades_disponibles = UnidadHabitacional.objects.all()[:3]

            for i, user_data in enumerate(usuarios_data):
                user, created = User.objects.get_or_create(
                    username=user_data['username'],
                    defaults={
                        **user_data,
                        'condominio': condominio,
                        'telefono': f'+591 7{random.randint(10000000, 99999999)}',
                        'cedula': f'{random.randint(10000000, 99999999)}'
                    }
                )
                if created:
                    user.set_password('password123')
                    user.save()
                    self.stdout.write(f'  ✓ Usuario creado: {user.get_full_name()}')

                if i < len(unidades_disponibles):
                    propietario, created = Propietario.objects.get_or_create(
                        user=user,
                        unidad=unidades_disponibles[i],
                        defaults={
                            'porcentaje_propiedad': Decimal('100.00'),
                            'fecha_inicio': (timezone.now() - timedelta(days=365)).date(),
                            'is_active': True
                        }
                    )
                    if created:
                        self.stdout.write(f'  ✓ Propietario creado: {propietario}')

    def create_sample_infracciones(self):
        """Crear infracciones de ejemplo en diferentes estados"""
        propietarios = list(Propietario.objects.all()[:3])
        admin_user = User.objects.filter(is_staff=True).first()

        if not propietarios:
            self.stdout.write(self.style.WARNING('No hay propietarios disponibles'))
            return

        infracciones_data = [
            {
                'propietario': propietarios[0],
                'tipo_infraccion': TipoInfraccion.RUIDO_EXCESIVO,
                'descripcion': 'Música a alto volumen después de las 22:00 horas',
                'fecha_infraccion': timezone.now() - timedelta(days=5),
                'estado': EstadoInfraccion.REGISTRADA,
                'reportado_por': admin_user,
            },
            {
                'propietario': propietarios[1],
                'tipo_infraccion': TipoInfraccion.MASCOTA_SIN_CORREA,
                'descripcion': 'Perro suelto en área de juegos infantiles',
                'fecha_infraccion': timezone.now() - timedelta(days=10),
                'estado': EstadoInfraccion.CONFIRMADA,
                'reportado_por': admin_user,
            },
            {
                'propietario': propietarios[2],
                'tipo_infraccion': TipoInfraccion.PARQUEADERO_INCORRECTO,
                'descripcion': 'Vehículo estacionado en área de visitas sin autorización',
                'fecha_infraccion': timezone.now() - timedelta(days=20),
                'estado': EstadoInfraccion.MULTA_APLICADA,
                'monto_multa': Decimal('120.00'),
                'fecha_limite_pago': (timezone.now() + timedelta(days=5)).date(),
                'reportado_por': admin_user,
            },
            {
                'propietario': propietarios[0],  # Reincidencia
                'tipo_infraccion': TipoInfraccion.RUIDO_EXCESIVO,
                'descripcion': 'Segunda infracción por ruido excesivo en horario nocturno',
                'fecha_infraccion': timezone.now() - timedelta(days=2),
                'estado': EstadoInfraccion.CONFIRMADA,
                'reportado_por': admin_user,
                'es_reincidente': True,
            },
        ]

        for infraccion_data in infracciones_data:
            infraccion = Infraccion.objects.create(
                unidad=infraccion_data['propietario'].unidad,
                **infraccion_data
            )
            self.stdout.write(f'  ✓ Infracción creada: {infraccion}')

    def create_sample_cargos(self):
        """Crear cargos de ejemplo incluyendo multas y otros tipos"""
        propietarios = list(Propietario.objects.all()[:3])
        infracciones = list(Infraccion.objects.all())

        if not propietarios:
            return

        # Crear cargo por multa (vinculado a infracción)
        if infracciones:
            infraccion_con_multa = next(
                (inf for inf in infracciones if inf.estado == EstadoInfraccion.MULTA_APLICADA),
                None
            )
            if infraccion_con_multa:
                cargo_multa = Cargo.objects.create(
                    propietario=infraccion_con_multa.propietario,
                    unidad=infraccion_con_multa.unidad,
                    concepto=f'Multa por {infraccion_con_multa.get_tipo_infraccion_display()}',
                    tipo_cargo=TipoCargo.MULTA,
                    monto=infraccion_con_multa.monto_multa,
                    fecha_vencimiento=infraccion_con_multa.fecha_limite_pago,
                    infraccion=infraccion_con_multa,
                    estado=EstadoCargo.PENDIENTE
                )
                self.stdout.write(f'  ✓ Cargo por multa creado: {cargo_multa}')

        # Crear cargos por cuotas mensuales
        for i, propietario in enumerate(propietarios):
            # Cuota mensual actual
            cargo_cuota = Cargo.objects.create(
                propietario=propietario,
                unidad=propietario.unidad,
                concepto='Cuota de administración - Septiembre 2025',
                tipo_cargo=TipoCargo.CUOTA_MENSUAL,
                monto=Decimal('250.00'),
                fecha_vencimiento=(timezone.now() + timedelta(days=30)).date(),
                es_recurrente=True,
                periodo='Septiembre 2025'
            )
            self.stdout.write(f'  ✓ Cuota mensual creada: {cargo_cuota}')

            # Cargo vencido para testear intereses de mora
            if i == 0:  # Solo para el primer propietario
                cargo_vencido = Cargo.objects.create(
                    propietario=propietario,
                    unidad=propietario.unidad,
                    concepto='Cuota de administración - Agosto 2025',
                    tipo_cargo=TipoCargo.CUOTA_MENSUAL,
                    monto=Decimal('250.00'),
                    fecha_vencimiento=(timezone.now() - timedelta(days=15)).date(),
                    es_recurrente=True,
                    periodo='Agosto 2025',
                    estado=EstadoCargo.VENCIDO
                )
                self.stdout.write(f'  ✓ Cargo vencido creado: {cargo_vencido}')

        # Crear expensa extraordinaria
        if len(propietarios) >= 2:
            expensa = Cargo.objects.create(
                propietario=propietarios[1],
                unidad=propietarios[1].unidad,
                concepto='Expensa extraordinaria - Reparación de ascensor',
                tipo_cargo=TipoCargo.EXPENSA_EXTRAORDINARIA,
                monto=Decimal('180.00'),
                fecha_vencimiento=(timezone.now() + timedelta(days=20)).date(),
                periodo='Septiembre 2025'
            )
            self.stdout.write(f'  ✓ Expensa extraordinaria creada: {expensa}')

    def show_summary(self):
        """Mostrar resumen de datos creados"""
        self.stdout.write('\nRESUMEN DE DATOS CREADOS:')
        self.stdout.write(f'  - Configuraciones de multas: {ConfiguracionMultas.objects.count()}')
        self.stdout.write(f'  - Infracciones: {Infraccion.objects.count()}')
        self.stdout.write(f'  - Cargos: {Cargo.objects.count()}')
        self.stdout.write(f'  - Propietarios: {Propietario.objects.count()}')

        self.stdout.write('\nDATOS PARA TESTING:')
        self.stdout.write('  Puedes usar estos endpoints para probar:')
        self.stdout.write('  - GET /api/finances/api/infracciones/')
        self.stdout.write('  - GET /api/finances/api/cargos/')
        self.stdout.write('  - GET /api/finances/api/configuracion-multas/')
        self.stdout.write('  - GET /api/finances/api/infracciones/pendientes/')
        self.stdout.write('  - GET /api/finances/api/cargos/vencidos/')

        self.stdout.write('\nAUTENTICACION:')
        self.stdout.write('  Necesitas autenticarte para usar las APIs')
        self.stdout.write('  Usa el admin: admin / admin123')
        self.stdout.write('  Admin en: http://127.0.0.1:8000/admin/')