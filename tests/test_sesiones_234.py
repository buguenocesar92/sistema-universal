"""
test_sesiones_234.py — Tests de los modulos de Sesion 2, 3 y 4
"""
import os, sys, unittest, tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


class TestI18n(unittest.TestCase):
    def test_carga_traduccion_es(self):
        from jobs.i18n import t
        r = t("portal.titulo", lang="es")
        self.assertIn("Portal", r)

    def test_carga_traduccion_en(self):
        from jobs.i18n import t
        r = t("portal.titulo", lang="en")
        self.assertIn("portal", r.lower())

    def test_clave_inexistente_devuelve_clave(self):
        from jobs.i18n import t
        r = t("nada.que.existe", lang="es")
        self.assertEqual(r, "nada.que.existe")

    def test_idiomas_disponibles(self):
        from jobs.i18n import idiomas_disponibles
        idiomas = idiomas_disponibles()
        self.assertIn("es", idiomas)
        self.assertIn("en", idiomas)


class TestCrypto(unittest.TestCase):
    def test_cifrar_descifrar_ida_vuelta(self):
        from jobs.crypto import cifrar, descifrar
        original = "datos sensibles 123"
        cifrado = cifrar(original)
        self.assertNotEqual(cifrado, original)
        descifrado = descifrar(cifrado)
        self.assertEqual(descifrado, original)

    def test_cifrar_vacio_no_rompe(self):
        from jobs.crypto import cifrar, descifrar
        self.assertEqual(cifrar(""), "")
        self.assertEqual(descifrar(""), "")

    def test_cifrar_dict_solo_campos_sensibles(self):
        from jobs.crypto import cifrar_dict, descifrar_dict
        datos = {
            "nombre":   "Juan Perez",
            "rut":      "12345678-9",
            "email":    "juan@test.cl",
            "salario":  1500000,
        }
        cifrado = cifrar_dict(datos)
        # Nombre y email no son sensibles
        self.assertEqual(cifrado["nombre"], "Juan Perez")
        self.assertEqual(cifrado["email"], "juan@test.cl")
        # Rut y salario sí deben cifrarse
        self.assertNotEqual(cifrado["rut"], "12345678-9")
        self.assertNotEqual(cifrado["salario"], 1500000)

        descifrado = descifrar_dict(cifrado)
        self.assertEqual(descifrado["rut"], "12345678-9")


class TestJWT(unittest.TestCase):
    def test_emitir_tokens_estructura(self):
        from jobs.jwt_auth import emitir_tokens
        r = emitir_tokens(user_id=1, rol="admin", empresa=None)
        self.assertIn("access", r)
        self.assertIn("refresh", r)
        self.assertIn("expira_en", r)
        self.assertEqual(r["type"], "Bearer")

    def test_verificar_access_valido(self):
        from jobs.jwt_auth import emitir_tokens, verificar_access
        tokens = emitir_tokens(user_id=42, rol="empresa", empresa="adille")
        payload = verificar_access(tokens["access"])
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], 42)
        self.assertEqual(payload["rol"], "empresa")
        self.assertEqual(payload["empresa"], "adille")

    def test_verificar_token_invalido(self):
        from jobs.jwt_auth import verificar_access
        self.assertIsNone(verificar_access("token_basura"))
        self.assertIsNone(verificar_access(""))
        self.assertIsNone(verificar_access(None))

    def test_refresh_token_no_sirve_como_access(self):
        from jobs.jwt_auth import emitir_tokens, verificar_access
        tokens = emitir_tokens(user_id=1, rol="admin")
        # Intentar usar el refresh como access debe fallar
        resultado = verificar_access(tokens["refresh"])
        self.assertIsNone(resultado)


class TestVault(unittest.TestCase):
    def test_get_secret_desde_env(self):
        from jobs.vault import get_secret
        os.environ["TEST_VAULT_KEY_UNICO"] = "valor_del_env"
        self.assertEqual(get_secret("TEST_VAULT_KEY_UNICO"), "valor_del_env")
        del os.environ["TEST_VAULT_KEY_UNICO"]

    def test_get_secret_default(self):
        from jobs.vault import get_secret
        self.assertEqual(
            get_secret("SECRETO_QUE_NO_EXISTE_JAMAS", default="fallback"),
            "fallback"
        )

    def test_get_secret_descifra_enc_prefix(self):
        from jobs.vault import get_secret
        from jobs.crypto import cifrar
        cifrado = "enc:" + cifrar("valor_real_cifrado")
        os.environ["TEST_SECRETO_CIFRADO"] = cifrado
        resultado = get_secret("TEST_SECRETO_CIFRADO")
        self.assertEqual(resultado, "valor_real_cifrado")
        del os.environ["TEST_SECRETO_CIFRADO"]


class TestRateLimit(unittest.TestCase):
    def test_limites_configurados(self):
        from jobs.rate_limit_smart import LIMITES
        self.assertIn("anonimo", LIMITES)
        self.assertIn("autenticado", LIMITES)
        self.assertIn("admin", LIMITES)
        self.assertLess(LIMITES["anonimo"], LIMITES["autenticado"])
        self.assertLess(LIMITES["autenticado"], LIMITES["admin"])


class TestTwoFactor(unittest.TestCase):
    def setUp(self):
        # Crear DB temporal con usuario
        import jobs.auth as auth
        import jobs.two_factor as tf

        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._orig_auth = auth.DB_PATH
        self._orig_tf   = tf.DB_PATH
        auth.DB_PATH = Path(self.tmp.name)
        tf.DB_PATH   = Path(self.tmp.name)
        auth._init_db()
        tf._init_tabla()

        self.auth = auth
        self.tf = tf

        auth.crear_usuario("2fa@test.cl", "pass123", "admin")

    def tearDown(self):
        self.auth.DB_PATH = self._orig_auth
        self.tf.DB_PATH = self._orig_tf
        os.unlink(self.tmp.name)

    def test_activar_2fa_genera_qr(self):
        r = self.tf.activar_2fa("2fa@test.cl")
        self.assertIn("qr_url", r)
        self.assertTrue(r["qr_url"].startswith("otpauth://"))
        self.assertEqual(len(r["backup_codes"]), 8)

    def test_confirmar_con_codigo_totp(self):
        import pyotp
        r = self.tf.activar_2fa("2fa@test.cl")
        totp = pyotp.TOTP(r["secret"])
        codigo = totp.now()
        self.assertTrue(self.tf.confirmar_2fa("2fa@test.cl", codigo))

    def test_confirmar_con_codigo_falso(self):
        self.tf.activar_2fa("2fa@test.cl")
        self.assertFalse(self.tf.confirmar_2fa("2fa@test.cl", "000000"))

    def test_backup_code_se_consume(self):
        import pyotp
        r = self.tf.activar_2fa("2fa@test.cl")
        # Primero activar con TOTP
        totp = pyotp.TOTP(r["secret"])
        self.tf.confirmar_2fa("2fa@test.cl", totp.now())
        # Ahora usar un backup code
        codigo_backup = r["backup_codes"][0]
        self.assertTrue(self.tf.verificar_2fa("2fa@test.cl", codigo_backup))
        # El mismo backup ya no debería funcionar
        self.assertFalse(self.tf.verificar_2fa("2fa@test.cl", codigo_backup))


class TestNotifications(unittest.TestCase):
    def test_enviar_email_sin_smtp_devuelve_error(self):
        # Sin SMTP configurado, debe retornar error sin crashear
        os.environ.pop("SMTP_USER", None)
        os.environ.pop("SMTP_PASS", None)
        from jobs.notifications import enviar_email
        r = enviar_email("test@test.cl", "asunto", "<p>hola</p>")
        self.assertFalse(r["ok"])
        self.assertIn("error", r)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestMJMLTemplates(unittest.TestCase):
    def test_compilar_mjml_basico(self):
        from jobs.mjml_templates import compilar_mjml
        mjml = "<mjml><mj-body><mj-text>Hola</mj-text></mj-body></mjml>"
        html = compilar_mjml(mjml)
        self.assertIn("<html>", html)
        self.assertIn("Hola", html)

    def test_render_template_reemplaza_variables(self):
        from jobs.mjml_templates import render_template
        html = render_template("reporte_base",
            titulo="Test",
            subtitulo="Sub",
            nombre_destinatario="Juan",
            mensaje="mensaje test",
            contenido_datos="",
            url_detalle="https://test.cl",
            fecha="2026-04-19"
        )
        self.assertIn("Test", html)
        self.assertIn("Juan", html)
        self.assertNotIn("{{titulo}}", html)

    def test_render_template_inexistente_devuelve_vacio(self):
        from jobs.mjml_templates import render_template
        self.assertEqual(render_template("template_que_no_existe"), "")


class TestDriveExport(unittest.TestCase):
    def test_subir_backup_sin_archivo_retorna_error(self):
        from jobs.drive_export import subir_backup
        from pathlib import Path
        r = subir_backup(Path("/tmp/no_existe_este_archivo_xyz.tar.gz"))
        self.assertFalse(r["ok"])
        self.assertIn("error", r)

    def test_limpiar_antiguos_sin_creds(self):
        from jobs.drive_export import limpiar_antiguos
        r = limpiar_antiguos(dias=30)
        # Sin creds, debe retornar error controlado, no crashear
        self.assertIn("eliminados", r)
