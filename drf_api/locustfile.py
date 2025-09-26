from locust import HttpUser, task, between
import random
import requests
from queue import Queue
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일 로드

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

USER_CREDENTIALS = Queue()
for i in range(1, 11):
    USER_CREDENTIALS.put({"email": f"test{i}@naver.com", "password": "123456"})
class NoteUser(HttpUser):
    wait_time = between(1, 3)
    note_ids = []  # 테스트용 노트 ID 목록

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


    # def on_stop(self):
    #     if hasattr(self, "created_note_id"):
    #         response = self.client.delete(f"/api/notes/{self.created_note_id}/delete/")
    #         if response.status_code != 204:
    #             print(f"❌ 노트 삭제 실패 (id={self.created_note_id}) - status {response.status_code}")
    #         else:
    #             print(f"✅ 노트 삭제 완료 (id={self.created_note_id})")



    @task(1)
    def explore_mypage(self):
        self.client.get("/api/friends/")


    # @task(1)
    # def explore_create_friend(self):
    #     self.client.get("/api/friends/requests/")

    # @task(2)
    # def get_note_detail(self):
    #     if self.note_ids:
    #         note_id = self.created_note_id
    #         self.client.get(f"/api/notes/{note_id}/")

    # @task(1)
    # def get_note_home(self):
    #     params = [
    #         {"type": "all", "sort": "recent"},
    #         {"type": "shared", "sort": "likes"},
    #         {"type": "public", "sort": "views"},
    #         {"type": "private", "sort": "comments"}
    #     ]
    #     param = random.choice(params)
    #     self.client.get("/api/notes/home/", params=param)

    # @task(1)
    # def update_note(self):
    #     if self.note_ids:
    #         note_id = self.created_note_id
    #         data = {
    #             "file_name": f"update Note {random.randint(1, 1000)}",
    #             "title": f"update Title {random.randint(1, 1000)}",
    #             "content": [
    #                 {"type": "paragraph", "content": [{"type": "text", "text": "수정된 내용입니다."}]},
    #                 {"type": "paragraph"}
    #             ]
    #         }
    #         self.client.patch(f"/api/notes/{note_id}/edit/", json=data)


