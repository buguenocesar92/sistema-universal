"""
test_jobs.py — Tests para los módulos de Sesión 1
Cubre: queue, cache, audit, auth, backup, sentry
"""
import os, sys, unittest, tempfile, time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


class TestAuditLog(unittest.TestCase):
    """Tests del audit log (no necesita Redis)"""

    def setUp(self):
        # Usar BD temporal para los tests
        self.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp_db.close()
        # Monkey-patch la ruta de DB
        import jobs.audit as audit
        self._orig_db = audit.DB_PATH
        audit.DB_PATH = Path(self.tmp_db.name)
        audit._init_db()
        self.audit = audit

    def tearDown(self):
        self.audit.DB_PATH = self._orig_db
        os.unlink(self.tmp_db.name)

    def test_log_action_guarda_registro(self):
        self.audit.log_action(
            accion="test_accion",
            usuario="tester@kraftdo.cl",
            empresa="adille",
            ip="127.0.0.1",
        )
        logs = self.audit.query_logs(usuario="tester@kraftdo.cl")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["accion"], "test_accion")
        self.assertEqual(logs[0]["empresa"], "adille")

    def test_query_filtra_por_empresa(self):
        self.audit.log_action(accion="a1", empresa="adille")
        self.audit.log_action(accion="a2", empresa="extractores")
        self.audit.log_action(accion="a3", empresa="adille")

        adille_logs = self.audit.query_logs(empresa="adille")
        self.assertEqual(len(adille_logs), 2)

        extr_logs = self.audit.query_logs(empresa="extractores")
        self.assertEqual(len(extr_logs), 1)

    def test_stats_agrupa_correctamente(self):
        self.audit.log_action(accion="upload", empresa="adille")
        self.audit.log_action(accion="upload", empresa="adille")
        self.audit.log_action(accion="crear", empresa="extractores")

        stats = self.audit.stats()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["acciones"]["upload"], 2)
        self.assertEqual(stats["empresas"]["adille"], 2)

    def test_detalle_json_se_persiste(self):
        self.audit.log_action(
            accion="crear",
            detalle={"sku": "ABC-123", "precio": 5000},
        )
        logs = self.audit.query_logs(accion="crear")
        import json
        detalle = json.loads(logs[0]["detalle"])
        self.assertEqual(detalle["sku"], "ABC-123")
        self.assertEqual(detalle["precio"], 5000)


class TestAuth(unittest.TestCase):
    """Tests del sistema de permisos por rol"""

    def setUp(self):
        self.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp_db.close()
        import jobs.auth as auth
        self._orig_db = auth.DB_PATH
        auth.DB_PATH = Path(self.tmp_db.name)
        auth._init_db()
        self.auth = auth

    def tearDown(self):
        self.auth.DB_PATH = self._orig_db
        os.unlink(self.tmp_db.name)

    def test_crear_admin(self):
        usr = self.auth.crear_usuario("cesar@kraftdo.cl", "secret123", rol="admin")
        self.assertEqual(usr["rol"], "admin")

    def test_crear_empresa_requiere_empresa(self):
        with self.assertRaises(ValueError):
            self.auth.crear_usuario("jonathan@adille.cl", "pass", rol="empresa")

    def test_login_con_credenciales_correctas(self):
        self.auth.crear_usuario("admin@test.cl", "password", rol="admin")
        sesion = self.auth.login("admin@test.cl", "password")
        self.assertIsNotNone(sesion)
        self.assertTrue(len(sesion["token"]) > 20)

    def test_login_con_password_incorrecto(self):
        self.auth.crear_usuario("admin@test.cl", "password", rol="admin")
        sesion = self.auth.login("admin@test.cl", "incorrecto")
        self.assertIsNone(sesion)

    def test_verificar_token_valido(self):
        self.auth.crear_usuario("admin@test.cl", "password", rol="admin")
        sesion = self.auth.login("admin@test.cl", "password")
        usr = self.auth.verificar_token(sesion["token"])
        self.assertIsNotNone(usr)
        self.assertEqual(usr["email"], "admin@test.cl")

    def test_verificar_token_invalido(self):
        self.assertIsNone(self.auth.verificar_token("token_falso"))
        self.assertIsNone(self.auth.verificar_token(""))
        self.assertIsNone(self.auth.verificar_token(None))

    def test_permisos_admin_accede_todo(self):
        admin = {"rol": "admin", "empresa": None}
        self.assertTrue(self.auth.puede_acceder(admin, "adille"))
        self.assertTrue(self.auth.puede_acceder(admin, "extractores", "editar"))

    def test_permisos_empresa_solo_su_empresa(self):
        jonathan = {"rol": "empresa", "empresa": "adille"}
        self.assertTrue(self.auth.puede_acceder(jonathan, "adille"))
        self.assertTrue(self.auth.puede_acceder(jonathan, "adille", "editar"))
        self.assertFalse(self.auth.puede_acceder(jonathan, "extractores"))

    def test_permisos_lector_no_puede_editar(self):
        karen = {"rol": "lector", "empresa": "adille"}
        self.assertTrue(self.auth.puede_acceder(karen, "adille", "ver"))
        self.assertFalse(self.auth.puede_acceder(karen, "adille", "editar"))


class TestCache(unittest.TestCase):
    """Tests del cache — funciona sin Redis (fallback transparente)"""

    def test_cached_sin_redis_no_rompe(self):
        from jobs.cache import cached
        llamadas = [0]

        @cached("test_ns", ttl=60)
        def fn(x):
            llamadas[0] += 1
            return x * 2

        r1 = fn(5)
        r2 = fn(5)
        self.assertEqual(r1, 10)
        self.assertEqual(r2, 10)
        # Sin Redis, cada llamada se ejecuta (no hay cache)
        # Con Redis, llamadas[0] == 1

    def test_invalidar_no_rompe(self):
        from jobs.cache import invalidar
        count = invalidar("namespace_que_no_existe")
        self.assertIsInstance(count, int)

    def test_estadisticas_responde(self):
        from jobs.cache import estadisticas
        stats = estadisticas()
        self.assertIsInstance(stats, dict)


class TestQueue(unittest.TestCase):
    """Tests de la queue — el fallback funciona sin Redis"""

    def test_queue_sin_redis(self):
        from jobs.queue import JobQueue
        q = JobQueue()
        # ok=False si no hay Redis en el entorno de test
        self.assertIn(q.ok, [True, False])

    def test_enqueue_sin_redis_no_rompe(self):
        from jobs.queue import JobQueue
        q = JobQueue()
        # Enqueue devuelve un job_id incluso sin Redis
        job_id = q.enqueue("test", {"x": 1})
        self.assertTrue(job_id.startswith("job_"))

    def test_status_sin_redis(self):
        from jobs.queue import JobQueue
        q = JobQueue()
        status = q.status("job_inexistente")
        self.assertIn(status, ("sin_redis", "desconocido", "pendiente"))

    def test_handler_decorator(self):
        from jobs.queue import handler, HANDLERS

        @handler("test_tipo_unico_xyz")
        def mi_handler(payload):
            return {"ok": True}

        self.assertIn("test_tipo_unico_xyz", HANDLERS)


class TestSentry(unittest.TestCase):
    """Tests del modulo de Sentry (fallback por email si no hay DSN)"""

    def test_init_sin_dsn_no_rompe(self):
        from jobs.sentry_config import init_sentry
        # Sin SENTRY_DSN debería retornar False pero no crashear
        resultado = init_sentry()
        self.assertIsInstance(resultado, bool)

    def test_capturar_error_sin_sentry_no_rompe(self):
        from jobs.sentry_config import capturar_error
        try:
            raise ValueError("test error")
        except Exception as e:
            # No debería lanzar excepción, aunque no haya Sentry ni SMTP
            capturar_error(e, contexto={"test": "unittest"})


class TestGeneratorIndices(unittest.TestCase):
    """Tests de que el generator produce índices automáticos"""

    def test_auto_indices_detecta_fecha(self):
        from generator import _auto_indices
        cols = {"id": "A", "fecha": "B", "monto": "C"}
        indices = _auto_indices(cols)
        self.assertIn("fecha", indices)

    def test_auto_indices_detecta_estado_sku_email(self):
        from generator import _auto_indices
        cols = {"id": "A", "estado": "B", "sku": "C", "email": "D", "nombre": "E"}
        indices = _auto_indices(cols)
        self.assertIn("estado", indices)
        self.assertIn("sku", indices)
        self.assertIn("email", indices)

    def test_auto_indices_ignora_campos_comunes(self):
        from generator import _auto_indices
        cols = {"nombre": "A", "descripcion": "B", "observaciones": "C"}
        indices = _auto_indices(cols)
        # Ninguno de esos campos debería tener índice
        self.assertEqual(indices, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
