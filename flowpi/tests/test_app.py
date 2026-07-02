import os
import tempfile
import unittest


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["FLOWPI_DB_PATH"] = os.path.join(self.temp_dir.name, "flow.db")
        os.environ["FLOWPI_ENABLE_GPIO"] = "false"
        os.environ["FLOWPI_ADMIN_TOKEN"] = "secret-token"
        os.environ["FLOWPI_ADMIN_USERNAME"] = "admin"
        os.environ["FLOWPI_ADMIN_PASSWORD"] = "pass123"

        from backend.app import create_app

        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("FLOWPI_DB_PATH", None)
        os.environ.pop("FLOWPI_ENABLE_GPIO", None)
        os.environ.pop("FLOWPI_ADMIN_TOKEN", None)
        os.environ.pop("FLOWPI_ADMIN_USERNAME", None)
        os.environ.pop("FLOWPI_ADMIN_PASSWORD", None)

    def test_health_endpoint(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_rejects_unknown_user(self):
        response = self.client.post("/set_user/999")

        self.assertEqual(response.status_code, 404)

    def test_admin_volume_update_requires_token(self):
        response = self.client.post(
            "/admin/users/1/volume",
            json={"total_ml": 1500},
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_update_user_volume(self):
        response = self.client.post(
            "/admin/users/1/volume",
            json={"total_ml": 1750},
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["user_id"], 1)
        self.assertAlmostEqual(body["total_ml"], 1750.0)

        totals_response = self.client.get("/user_totals")
        totals = totals_response.get_json()
        user_one = next(item for item in totals if item["id"] == 1)
        self.assertAlmostEqual(float(user_one["ml"]), 1750.0)

    def test_admin_login_rejects_invalid_credentials(self):
        response = self.client.post(
            "/admin/login",
            json={"username": "admin", "password": "wrong"},
        )

        self.assertEqual(response.status_code, 401)

    def test_admin_can_update_user_volume_with_session(self):
        login = self.client.post(
            "/admin/login",
            json={"username": "admin", "password": "pass123"},
        )
        self.assertEqual(login.status_code, 200)
        session_token = login.get_json()["session_token"]

        response = self.client.post(
            "/admin/users/2/volume",
            json={"total_ml": 900},
            headers={"X-Admin-Session": session_token},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["user_id"], 2)
        self.assertAlmostEqual(body["total_ml"], 900.0)

    def test_admin_can_update_user_name_with_session(self):
        login = self.client.post(
            "/admin/login",
            json={"username": "admin", "password": "pass123"},
        )
        self.assertEqual(login.status_code, 200)
        session_token = login.get_json()["session_token"]

        response = self.client.post(
            "/admin/users/2/name",
            json={"name": "Alex"},
            headers={"X-Admin-Session": session_token},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["user_id"], 2)
        self.assertEqual(body["name"], "Alex")

        totals_response = self.client.get("/user_totals")
        totals = totals_response.get_json()
        user_two = next(item for item in totals if item["id"] == 2)
        self.assertEqual(user_two["name"], "Alex")

    def test_admin_can_add_user_with_session(self):
        login = self.client.post(
            "/admin/login",
            json={"username": "admin", "password": "pass123"},
        )
        self.assertEqual(login.status_code, 200)
        session_token = login.get_json()["session_token"]

        response = self.client.post(
            "/admin/users",
            json={"name": "Guest"},
            headers={"X-Admin-Session": session_token},
        )

        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["name"], "Guest")

        totals = self.client.get("/user_totals").get_json()
        self.assertTrue(any(user["name"] == "Guest" for user in totals))

    def test_admin_can_delete_user_with_session(self):
        login = self.client.post(
            "/admin/login",
            json={"username": "admin", "password": "pass123"},
        )
        self.assertEqual(login.status_code, 200)
        session_token = login.get_json()["session_token"]

        create_response = self.client.post(
            "/admin/users",
            json={"name": "Temp"},
            headers={"X-Admin-Session": session_token},
        )
        self.assertEqual(create_response.status_code, 201)
        created_user_id = create_response.get_json()["id"]

        delete_response = self.client.delete(
            f"/admin/users/{created_user_id}",
            headers={"X-Admin-Session": session_token},
        )
        self.assertEqual(delete_response.status_code, 200)

        totals = self.client.get("/user_totals").get_json()
        self.assertFalse(any(user["id"] == created_user_id for user in totals))


if __name__ == "__main__":
    unittest.main()