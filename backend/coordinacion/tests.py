from datetime import timedelta

from django.utils import timezone

from coordinacion.models import Tarea
from cuentas.tests import BaseAuthTest


class CrearTareaTests(BaseAuthTest):
    def datos(self, curso):
        return {'titulo': 'Ensayo', 'descripcion': 'd', 'curso': curso.id,
                'fecha_vencimiento': (timezone.now() + timedelta(days=3)).isoformat()}

    def test_se_asigna_a_los_alumnos_del_curso(self):
        self.client.force_authenticate(self.profe)
        r = self.client.post('/api/tareas/', self.datos(self.curso))
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['curso_nombre'], 'Mate')
        self.assertEqual(list(Tarea.objects.get().estudiantes.all()), [self.ana])

    def test_estudiante_no_crea_tareas(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.post('/api/tareas/', self.datos(self.curso)).status_code, 403)
