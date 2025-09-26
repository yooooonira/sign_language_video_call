from locust import HttpUser, task, between
import random
import requests
from queue import Queue
from dotenv import load_dotenv
import os
from typing import Dict

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
                "apikey": SUPABASE_ANON_KEY,   # anon key 사용
                "Content-Type": "application/json"
            },
            json={
                "email": self.user["email"],
                "password": self.user["password"]
            }
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
            raise Exception(f"Failed to login as {self.user['email']} – {auth_response.text}")

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

    @task(1)
    def get_friend_detail(self):
        """친구 프로필 상세 조회"""
        # 먼저 친구 목록을 가져와서 랜덤하게 한 명 선택
        response = self.client.get("/api/friends/")
        if response.status_code == 200:
            friends_data = response.json()
            # pagination이 적용되어 있으므로 results 키에서 데이터 추출
            if friends_data.get("results") and len(friends_data["results"]) > 0:
                friend = random.choice(friends_data["results"])
                friend_id = friend.get("id")
                if friend_id:
                    self.client.get(f"/api/friends/{friend_id}/")
