"""
Locust load test for the ME Skin & Scalp Assistant backend.

Run (Django must be running on :8000):
    source venv/bin/activate
    locust                       # then open http://localhost:8089
  or headless (no UI):
    locust --headless -u 50 -r 5 -t 1m --host http://localhost:8000

  -u 50  → simulate 50 concurrent users
  -r 5   → spawn 5 users/second
  -t 1m  → run for 1 minute
"""
from locust import HttpUser, task, between


class FypUser(HttpUser):
    # Each simulated user waits 1-3s between actions (realistic browsing).
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    def on_start(self):
        """Log in once per simulated user and store the JWT token."""
        r = self.client.post(
            "/api/auth/login/",
            json={"email": "ali@gmail.com", "password": "ali@1234"},
            name="POST /api/auth/login/",
        )
        try:
            self.token = r.json().get("access", "")
        except Exception:
            self.token = ""

    def _auth(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(3)
    def stats(self):
        self.client.get("/api/analysis/stats/",
                        headers=self._auth(),
                        name="GET /api/analysis/stats/")

    @task(2)
    def history(self):
        self.client.get("/api/analysis/history/",
                        headers=self._auth(),
                        name="GET /api/analysis/history/")

    @task(1)
    def profile(self):
        self.client.get("/api/profile/",
                        headers=self._auth(),
                        name="GET /api/profile/")
