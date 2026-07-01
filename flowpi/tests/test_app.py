import os
import tempfile
import unittest


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["FLOWPI_DB_PATH"] = os.path.join(self.temp_dir.name, "flow.db")
        os.environ["FLOWPI_ENABLE_GPIO"] = "false"

        from backend.app import create_app

        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("FLOWPI_DB_PATH", None)
        os.environ.pop("FLOWPI_ENABLE_GPIO", None)

    def test_health_endpoint(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_rejects_unknown_user(self):
        response = self.client.post("/set_user/999")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()