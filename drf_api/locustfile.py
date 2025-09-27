import os
import requests
from locust import HttpUser, between, task

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

EMAIL = "test1@naver.com"
PASSWORD = "123456"

class NoteUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # 로그인해서 토큰 받아오기
        resp = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
            json={"email": EMAIL, "password": PASSWORD},
        )
        if resp.status_code != 200:
            raise Exception(f"Failed login: {resp.text}")

        access_token = resp.json()["access_token"]

        # Locust 요청 헤더에 넣기
        self.client.headers = {
            "Authorization": f"Bearer {access_token}",
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        }

    @task
    def explore_mypage(self):
        self.client.get("/api/friends/")

    @task
    def get_received_requests(self):
        self.client.get("/api/friends/requests/received/")

    @task
    def get_sent_requests(self):
        self.client.get("/api/friends/requests/sent/")
