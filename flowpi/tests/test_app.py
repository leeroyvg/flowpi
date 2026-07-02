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
        from backend.repository import create_user

        self.app = create_app()
        self.client = self.app.test_client()
        self.user1_id = create_user("User 1")
        self.user2_id = create_user("User 2")
        self.user3_id = create_user("User 3")

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

    def test_ready_endpoint(self):
        response = self.client.get("/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ready")

    def test_security_headers_present(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(response.headers.get("Referrer-Policy"), "no-referrer")

    def test_rejects_unknown_user(self):
        response = self.client.post("/set_user/999")

        self.assertEqual(response.status_code, 404)

    def test_admin_volume_update_requires_token(self):
        response = self.client.post(
            f"/admin/users/{self.user1_id}/volume",
            json={"total_ml": 1500},
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_update_user_volume(self):
        response = self.client.post(
            f"/admin/users/{self.user1_id}/volume",
            json={"total_ml": 1750},
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["user_id"], self.user1_id)
        self.assertAlmostEqual(body["total_ml"], 1750.0)

        totals_response = self.client.get("/user_totals")
        totals = totals_response.get_json()
        user_one = next(item for item in totals if item["id"] == self.user1_id)
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
            f"/admin/users/{self.user2_id}/volume",
            json={"total_ml": 900},
            headers={"X-Admin-Session": session_token},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["user_id"], self.user2_id)
        self.assertAlmostEqual(body["total_ml"], 900.0)

    def test_admin_can_update_user_name_with_session(self):
        login = self.client.post(
            "/admin/login",
            json={"username": "admin", "password": "pass123"},
        )
        self.assertEqual(login.status_code, 200)
        session_token = login.get_json()["session_token"]

        response = self.client.post(
            f"/admin/users/{self.user2_id}/name",
            json={"name": "Alex"},
            headers={"X-Admin-Session": session_token},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["user_id"], self.user2_id)
        self.assertEqual(body["name"], "Alex")

        totals_response = self.client.get("/user_totals")
        totals = totals_response.get_json()
        user_two = next(item for item in totals if item["id"] == self.user2_id)
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

    def test_tap_stats_returns_average_per_tap(self):
        from backend.repository import insert_flow

        before = self.client.get("/tap_stats").get_json()

        insert_flow(self.user1_id, 0, "TAP_OPEN")
        insert_flow(self.user1_id, 400, "FLOW")
        insert_flow(self.user1_id, 0, "TAP_CLOSE")

        insert_flow(self.user1_id, 0, "TAP_OPEN")
        insert_flow(self.user1_id, 600, "FLOW")
        insert_flow(self.user1_id, 0, "TAP_CLOSE")

        response = self.client.get("/tap_stats")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["tap_count"], before["tap_count"] + 2)
        self.assertAlmostEqual(body["total_flow_ml"], before["total_flow_ml"] + 1000.0)

        expected_avg = body["total_flow_ml"] / body["tap_count"]
        self.assertAlmostEqual(body["avg_ml_per_tap"], expected_avg)

    def test_tap_sessions_returns_recent_session_amounts(self):
        from backend.repository import insert_flow

        insert_flow(self.user2_id, 0, "TAP_OPEN")
        insert_flow(self.user2_id, 250, "FLOW")
        insert_flow(self.user2_id, 150, "FLOW")
        insert_flow(self.user2_id, 0, "TAP_CLOSE")

        insert_flow(self.user3_id, 0, "TAP_OPEN")
        insert_flow(self.user3_id, 500, "FLOW")
        insert_flow(self.user3_id, 0, "TAP_CLOSE")

        response = self.client.get("/tap_sessions")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()

        self.assertTrue(any(item["user_id"] == self.user2_id and item["state"] == "closed" and abs(float(item["total_ml"]) - 400.0) < 1e-6 for item in body))
        self.assertTrue(any(item["user_id"] == self.user3_id and item["state"] == "closed" and abs(float(item["total_ml"]) - 500.0) < 1e-6 for item in body))

    def test_admin_flow_events_requires_auth(self):
        response = self.client.get("/admin/flow_events")
        self.assertEqual(response.status_code, 403)

    def test_admin_flow_events_returns_logs(self):
        from backend.repository import insert_flow

        insert_flow(self.user1_id, 0, "TAP_OPEN")
        insert_flow(self.user1_id, 250, "FLOW")

        response = self.client.get(
            "/admin/flow_events?limit=5",
            headers={"X-Admin-Token": "secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(isinstance(body, list))
        self.assertGreaterEqual(len(body), 1)
        self.assertTrue(any(item["event"] in {"TAP_OPEN", "FLOW"} for item in body))
        self.assertTrue(any(item["user_id"] == self.user1_id and item["user_name"] == "User 1" for item in body))

    def test_public_flow_events_returns_logs_without_auth(self):
        from backend.repository import insert_flow

        insert_flow(self.user1_id, 0, "TAP_OPEN")
        insert_flow(self.user1_id, 300, "FLOW")

        response = self.client.get("/flow_events?limit=5")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(isinstance(body, list))
        self.assertGreaterEqual(len(body), 1)
        self.assertTrue(any(item["event"] in {"TAP_OPEN", "FLOW"} for item in body))


if __name__ == "__main__":
    unittest.main()