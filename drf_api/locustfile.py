import os
from queue import Queue
from typing import Dict

import requests
from dotenv import load_dotenv
from locust import HttpUser, between, task

load_dotenv()  # .env 파일 로드

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

USER_CREDENTIALS: Queue[Dict[str, str]] = Queue()
for i in range(1, 11):
    USER_CREDENTIALS.put({"email": f"test{i}@naver.com", "password": "123456"})


class NoteUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        if not USER_CREDENTIALS.empty():
            self.user = USER_CREDENTIALS.get()
        else:
            raise Exception("No more test users available")

        auth_response = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={
                "apikey": SUPABASE_ANON_KEY,  # anon key 사용
                "Content-Type": "application/json",
            },
            json={"email": self.user["email"], "password": self.user["password"]},
        )

        if auth_response.status_code == 200:
            self.token = auth_response.json().get("access_token")

            # 👉 Locust client 기본 헤더 세팅
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
