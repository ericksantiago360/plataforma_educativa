from cuentas.tests import BaseAuthTest


class InscripcionCursoTests(BaseAuthTest):
    def test_staff_inscribe_y_quita(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post(f'/api/cursos/{self.curso.id}/inscribir/', {'estudiante': self.beto.id})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(self.curso.estudiantes.filter(pk=self.beto.pk).exists())

        self.client.post(f'/api/cursos/{self.curso.id}/quitar/', {'estudiante': self.beto.id})
        self.assertFalse(self.curso.estudiantes.filter(pk=self.beto.pk).exists())

    def test_estudiante_invalido(self):
        self.client.force_authenticate(self.staff)
        for valor in ('', 'abc', 99999):
            r = self.client.post(f'/api/cursos/{self.curso.id}/inscribir/', {'estudiante': valor})
            self.assertEqual(r.status_code, 400)

    def test_profesor_no_inscribe(self):
        self.client.force_authenticate(self.profe)
        r = self.client.post(f'/api/cursos/{self.curso.id}/inscribir/', {'estudiante': self.beto.id})
        self.assertEqual(r.status_code, 403)

    def test_inscritos_para_profesor_pero_no_para_estudiante(self):
        self.client.force_authenticate(self.profe)
        r = self.client.get(f'/api/cursos/{self.curso.id}/inscritos/')
        self.assertEqual([e['id'] for e in r.data], [self.ana.id])

        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.get(f'/api/cursos/{self.curso.id}/inscritos/').status_code, 403)
