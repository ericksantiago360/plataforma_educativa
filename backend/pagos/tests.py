from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User

from cuentas.tests import BaseAuthTest
from estudiantes.models import Estudiante
from pagos.models import Cargo, ConceptoPago, Pago
from pagos.recibos import datos_recibo
from servicios.models import CentroIdiomas


class PagosBase(BaseAuthTest):
    def setUp(self):
        super().setUp()
        self.colegiatura = ConceptoPago.objects.create(nombre='Colegiatura', tipo='colegiatura', monto=Decimal('3500.00'))
        self.constancia = ConceptoPago.objects.create(nombre='Constancia de estudios', tipo='tramite', monto=Decimal('150.00'))
        self.cargo = Cargo.objects.create(estudiante=self.ana, concepto=self.colegiatura, descripcion='Colegiatura',
                                          tipo='colegiatura', monto=Decimal('3500.00'), periodo='2026-2')

    def pagar(self, monto, cargo=None, **extra):
        return self.client.post(f'/api/cargos/{(cargo or self.cargo).id}/pagar/',
                                {'monto': monto, 'metodo': 'efectivo', **extra})


class CargosTests(PagosBase):
    def test_staff_crea_cargo_desde_el_catalogo(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post('/api/cargos/', {'estudiante': self.beto.id, 'concepto': self.constancia.id,
                                              'fecha_limite': '2026-12-01'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.data['descripcion'], r.data['monto'], r.data['estado'], r.data['saldo']),
                         ('Constancia de estudios', '150.00', 'pendiente', '150.00'))

    def test_cargo_masivo_a_alumnos_activos_sin_duplicar(self):
        inactivo = Estudiante.objects.create(nombre='Ex', apellido='E', email='ex@x.com', matricula='9', activo=False)
        self.client.force_authenticate(self.staff)
        datos = {'concepto': self.colegiatura.id, 'periodo': '2026-2', 'fecha_limite': '2026-09-10'}
        r = self.client.post('/api/cargos/masivo/', datos)
        # Ana ya tenía la colegiatura de 2026-2: solo se crea la de Beto, y el inactivo no recibe cargo
        self.assertEqual((r.status_code, r.data), (201, {'creados': 1, 'ya_tenian': 1}))
        self.assertFalse(Cargo.objects.filter(estudiante=inactivo).exists())
        self.assertEqual(self.client.post('/api/cargos/masivo/', datos).data, {'creados': 0, 'ya_tenian': 2})

    def test_cargo_masivo_valida_concepto_y_periodo(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post('/api/cargos/masivo/', {'concepto': self.constancia.id, 'periodo': '2026-2'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('concepto', r.data)
        r = self.client.post('/api/cargos/masivo/', {'concepto': self.colegiatura.id, 'periodo': 'otoño'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('periodo', r.data)

    def test_cada_quien_ve_solo_sus_cargos(self):
        Cargo.objects.create(estudiante=self.beto, descripcion='x', tipo='tramite', monto=10)
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.ids('/api/cargos/'), {self.cargo.id})
        self.client.force_authenticate(self.profe)
        self.assertEqual(self.ids('/api/cargos/'), set())
        self.client.force_authenticate(self.staff)
        self.assertEqual(len(self.ids('/api/cargos/')), 2)
        self.assertEqual(self.ids(f'/api/cargos/?estudiante={self.ana.id}'), {self.cargo.id})

    def test_estudiante_y_profesor_no_crean_cargos_ni_pagos(self):
        for usuario in (self.u_ana, self.profe):
            self.client.force_authenticate(usuario)
            r = self.client.post('/api/cargos/', {'estudiante': self.ana.id, 'concepto': self.constancia.id})
            self.assertEqual(r.status_code, 403)
            self.assertEqual(self.pagar('100').status_code, 403)
            self.assertEqual(self.client.post(f'/api/cargos/{self.cargo.id}/cancelar/').status_code, 403)

    def test_los_cargos_no_se_editan_ni_se_borran(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.patch(f'/api/cargos/{self.cargo.id}/', {'monto': '1'}).status_code, 405)
        self.assertEqual(self.client.delete(f'/api/cargos/{self.cargo.id}/').status_code, 405)

    def test_cancelar_cargo_sin_pagos(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post(f'/api/cargos/{self.cargo.id}/cancelar/')
        self.assertEqual((r.data['estado'], r.data['saldo']), ('cancelado', '0.00'))

    def test_no_se_cancela_un_cargo_con_pagos(self):
        self.client.force_authenticate(self.staff)
        self.pagar('100')
        self.assertEqual(self.client.post(f'/api/cargos/{self.cargo.id}/cancelar/').status_code, 400)

    def test_cargo_vencido(self):
        Cargo.objects.filter(pk=self.cargo.pk).update(fecha_limite=date.today() - timedelta(days=1))
        self.client.force_authenticate(self.u_ana)
        self.assertTrue(self.client.get(f'/api/cargos/{self.cargo.id}/').data['vencido'])


class RegistrarPagoTests(PagosBase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.staff)

    def test_pagos_parciales_hasta_liquidar(self):
        r = self.pagar('1500', referencia='Caja 1')
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.data['estado'], r.data['pagado'], r.data['saldo']), ('parcial', '1500.00', '2000.00'))
        self.assertEqual(r.data['pago']['folio'], f"R-{r.data['pago']['id']:06d}")
        self.assertEqual(r.data['pago']['registrado_por_nombre'], 'staff')

        r = self.pagar('2000')
        self.assertEqual((r.data['estado'], r.data['saldo']), ('pagado', '0.00'))
        self.assertEqual(len(r.data['pagos']), 2)

    def test_no_se_paga_mas_que_el_saldo(self):
        self.pagar('3000')
        r = self.pagar('600')
        self.assertEqual(r.status_code, 400)
        self.assertIn('500.00', r.data['monto'][0])

    def test_monto_y_metodo_validos(self):
        for monto in ('0', '-5', 'abc'):
            self.assertEqual(self.pagar(monto).status_code, 400, monto)
        r = self.client.post(f'/api/cargos/{self.cargo.id}/pagar/', {'monto': '10', 'metodo': 'bitcoin'})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Pago.objects.exists())

    def test_no_se_paga_un_cargo_cancelado(self):
        self.client.post(f'/api/cargos/{self.cargo.id}/cancelar/')
        self.assertEqual(self.pagar('100').status_code, 400)

    def test_anular_pago_devuelve_el_saldo(self):
        pago_id = self.pagar('3500').data['pago']['id']
        url = f'/api/pagos/{pago_id}/anular/'
        self.assertEqual(self.client.post(url, {}).status_code, 400)  # el motivo es obligatorio

        r = self.client.post(url, {'motivo': 'Se capturó dos veces'})
        self.assertEqual((r.status_code, r.data['anulado']), (200, True))
        cargo = self.client.get(f'/api/cargos/{self.cargo.id}/').data
        self.assertEqual((cargo['estado'], cargo['saldo']), ('pendiente', '3500.00'))
        self.assertEqual(self.client.post(url, {'motivo': 'otra vez'}).status_code, 400)

    def test_estudiante_no_anula_pagos(self):
        pago_id = self.pagar('100').data['pago']['id']
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.post(f'/api/pagos/{pago_id}/anular/', {'motivo': 'x'}).status_code, 403)


class ReciboTests(PagosBase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.staff)
        self.pago_id = self.pagar('1000', referencia='SPEI 123').data['pago']['id']

    def test_alumno_descarga_su_recibo(self):
        self.client.force_authenticate(self.u_ana)
        r = self.client.get(f'/api/pagos/{self.pago_id}/recibo/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertIn(f'recibo-R-{self.pago_id:06d}.pdf', r['Content-Disposition'])
        self.assertTrue(r.content.startswith(b'%PDF'))

    def test_otros_no_ven_el_recibo(self):
        for usuario in (self.u_beto, self.profe):
            self.client.force_authenticate(usuario)
            self.assertEqual(self.client.get(f'/api/pagos/{self.pago_id}/recibo/').status_code, 404)

    def test_datos_del_recibo(self):
        datos = datos_recibo(Pago.objects.get())
        self.assertEqual((datos['concepto'], datos['monto'], datos['saldo'], datos['referencia'], datos['anulado']),
                         ('Colegiatura (2026-2)', '$1,000.00 MXN', '$2,500.00 MXN', 'SPEI 123', None))

    def test_el_saldo_del_recibo_no_cambia_con_pagos_posteriores(self):
        primero = Pago.objects.get()
        self.pagar('2500')
        self.assertEqual(datos_recibo(primero)['saldo'], '$2,500.00 MXN')
        self.assertEqual(datos_recibo(Pago.objects.exclude(pk=primero.pk).get())['saldo'], '$0.00 MXN')

    def test_motivo_con_caracteres_especiales(self):
        self.client.post(f'/api/pagos/{self.pago_id}/anular/', {'motivo': '<b>doble</b> & "cobro"'})
        self.assertEqual(self.client.get(f'/api/pagos/{self.pago_id}/recibo/').status_code, 200)

    def test_recibo_de_pago_anulado(self):
        self.client.post(f'/api/pagos/{self.pago_id}/anular/', {'motivo': 'Error de captura'})
        self.assertEqual(datos_recibo(Pago.objects.get())['anulado'], 'Error de captura')
        self.assertEqual(self.client.get(f'/api/pagos/{self.pago_id}/recibo/').status_code, 200)


class TramitesTests(PagosBase):
    def test_alumno_solicita_un_tramite(self):
        self.client.force_authenticate(self.u_ana)
        r = self.client.post('/api/cargos/solicitar_tramite/', {'concepto': self.constancia.id})
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.data['estudiante'], r.data['tipo'], r.data['monto']), (self.ana.id, 'tramite', '150.00'))

    def test_solo_tramites_activos_del_catalogo(self):
        self.client.force_authenticate(self.u_ana)
        inactivo = ConceptoPago.objects.create(nombre='Viejo', tipo='tramite', monto=1, activo=False)
        for concepto in (self.colegiatura.id, inactivo.id, 'abc'):
            self.assertEqual(self.client.post('/api/cargos/solicitar_tramite/', {'concepto': concepto}).status_code, 400)

    def test_profesor_no_solicita_tramites(self):
        self.client.force_authenticate(self.profe)
        r = self.client.post('/api/cargos/solicitar_tramite/', {'concepto': self.constancia.id})
        self.assertEqual(r.status_code, 403)

    def test_catalogo_solo_lo_edita_el_staff(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.post('/api/conceptos-pago/', {'nombre': 'x', 'tipo': 'tramite', 'monto': '1'}).status_code, 403)
        self.client.force_authenticate(self.staff)
        r = self.client.post('/api/conceptos-pago/', {'nombre': 'Credencial', 'tipo': 'tramite', 'monto': '80'})
        self.assertEqual(r.status_code, 201)
        r = self.client.post('/api/conceptos-pago/', {'nombre': 'x', 'tipo': 'idiomas', 'monto': '80'})
        self.assertEqual(r.status_code, 400)  # los cursos de idiomas cobran su propio precio


class IdiomasConCostoTests(PagosBase):
    def setUp(self):
        super().setUp()
        self.curso = CentroIdiomas.objects.create(idioma='frances', nivel='basico', nombre_curso='Francés I', descripcion='',
                                                  duracion_semanas=8, precio=Decimal('1200'), instructor='x',
                                                  fecha_inicio=date.today())
        self.client.force_authenticate(self.u_ana)

    def cargos_del_curso(self):
        return Cargo.objects.filter(curso_idiomas=self.curso)

    def test_inscribirse_genera_el_cargo_una_sola_vez(self):
        self.client.post(f'/api/idiomas/{self.curso.id}/inscribir/')
        self.client.post(f'/api/idiomas/{self.curso.id}/inscribir/')
        cargo = self.cargos_del_curso().get()
        self.assertEqual((cargo.estudiante, cargo.monto, cargo.tipo), (self.ana, Decimal('1200'), 'idiomas'))

    def test_cancelar_sin_pagos_cancela_el_cargo(self):
        self.client.post(f'/api/idiomas/{self.curso.id}/inscribir/')
        self.assertEqual(self.client.post(f'/api/idiomas/{self.curso.id}/cancelar/').status_code, 200)
        self.assertTrue(self.cargos_del_curso().get().cancelado)
        # Volver a inscribirse genera un cargo nuevo
        self.client.post(f'/api/idiomas/{self.curso.id}/inscribir/')
        self.assertEqual(self.cargos_del_curso().filter(cancelado=False).count(), 1)

    def test_no_se_cancela_un_curso_ya_pagado(self):
        self.client.post(f'/api/idiomas/{self.curso.id}/inscribir/')
        Pago.objects.create(cargo=self.cargos_del_curso().get(), monto=100, metodo='efectivo')
        r = self.client.post(f'/api/idiomas/{self.curso.id}/cancelar/')
        self.assertEqual(r.status_code, 400)
        self.assertTrue(self.curso.estudiantes_inscritos.filter(pk=self.ana.pk).exists())

    def test_cursos_gratuitos_no_generan_cargo(self):
        CentroIdiomas.objects.filter(pk=self.curso.pk).update(precio=0)
        self.client.post(f'/api/idiomas/{self.curso.id}/inscribir/')
        self.assertFalse(self.cargos_del_curso().exists())


class BorrarEstudianteConPagosTests(PagosBase):
    def test_no_se_borra_un_alumno_con_cargos(self):
        self.client.force_authenticate(self.staff)
        r = self.client.delete(f'/api/estudiantes/{self.ana.id}/')
        self.assertEqual(r.status_code, 400)
        self.assertTrue(Estudiante.objects.filter(pk=self.ana.pk).exists())

    def test_usuario_sin_rol_no_ve_pagos(self):
        self.client.force_authenticate(User.objects.create_user('nadie', password='x'))
        self.assertEqual(self.ids('/api/cargos/'), set())
        self.assertEqual(self.ids('/api/pagos/'), set())
