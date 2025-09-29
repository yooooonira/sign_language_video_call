import os
import random
from typing import Dict, List

import requests
from dotenv import load_dotenv
from locust import HttpUser, between, task

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

USER_CREDENTIALS: List[Dict[str, str]] = []
for i in range(1, 11):
    USER_CREDENTIALS.append({"email": f"test{i}@naver.com", "password": "123456"})


class NoteUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        if USER_CREDENTIALS:
            self.user = random.choice(USER_CREDENTIALS)
        else:
            raise Exception("No test users available")

        auth_response = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
            json={"email": self.user["email"], "password": self.user["password"]},
        )

        if auth_response.status_code == 200:
            self.token = auth_response.json().get("access_token")
            self.client.headers = {
                "Authorization": f"Bearer {self.token}",
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            }
        else:
            raise Exception(
                f"Failed to login as {self.user['email']} – {auth_response.text}"
            )

    @task(1)
    def explore_mypage(self):
        self.client.get("/api/friends/")

    @task(1)
    def get_received_requests(self):
        """친구 요청 받은 목록 조회"""
        self.client.get("/api/friends/requests/received/")

    @task(1)
    def get_sent_requests(self):
        """친구 요청 보낸 목록 조회"""
        self.client.get("/api/friends/requests/sent/")
