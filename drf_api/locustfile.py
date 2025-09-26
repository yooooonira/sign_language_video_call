from locust import HttpUser, task, between
import random
import requests
from queue import Queue
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일 로드

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

USER_CREDENTIALS = Queue()
for i in range(1, 11):
    USER_CREDENTIALS.put({"email": f"test{i}@naver.com", "password": "1234"})
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
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json"
            },
            json={
                "email": self.user["email"],
                "password": self.user["password"]
            }
        )

        if auth_response.status_code == 200:
            self.token = auth_response.json().get("access_token")
        else:
            raise Exception(f"Failed to login as {self.user['email']} – {auth_response.text}")

        self.client.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        data = {
            "name": f"LoadTest Note {random.randint(1000, 9999)}",
            "parent_id": None  # 필요하면 실제 folder-id로
        }
        response = self.client.post("/api/notes/note/", json=data)
        if response.status_code == 201:
            note = response.json()
            note_id = note["id"]  # 먼저 추출

            # "note-69" 같은 문자열이면 숫자만 추출
            if isinstance(note_id, str) and note_id.startswith("note-"):
                note_id = int(note_id.replace("note-", ""))

            self.note_ids = [note_id]  # 리스트에도 숫자 ID로 저장
            self.created_note_id = note_id  # 삭제용 ID 저장


        else:
            print("❌ 노트 생성 실패:")
            print("Status code:", response.status_code)
            print("Response body:", response.text)
            raise Exception("노트 생성 실패")

    # def on_stop(self):
    #     if hasattr(self, "created_note_id"):
    #         response = self.client.delete(f"/api/notes/{self.created_note_id}/delete/")
    #         if response.status_code != 204:
    #             print(f"❌ 노트 삭제 실패 (id={self.created_note_id}) - status {response.status_code}")
    #         else:
    #             print(f"✅ 노트 삭제 완료 (id={self.created_note_id})")

    @task(1)
    def explore_notes(self):
        self.client.get("/api/notes/explore/")

    @task(1)
    def get_note_list(self):
        self.client.get("/api/notes/sidebar/")

    @task(2)
    def get_note_detail(self):
        if self.note_ids:
            note_id = self.created_note_id
            self.client.get(f"/api/notes/{note_id}/")

    @task(1)
    def get_note_home(self):
        params = [
            {"type": "all", "sort": "recent"},
            {"type": "shared", "sort": "likes"},
            {"type": "public", "sort": "views"},
            {"type": "private", "sort": "comments"}
        ]
        param = random.choice(params)
        self.client.get("/api/notes/home/", params=param)

    @task(1)
    def update_note(self):
        if self.note_ids:
            note_id = self.created_note_id
            data = {
                "file_name": f"update Note {random.randint(1, 1000)}",
                "title": f"update Title {random.randint(1, 1000)}",
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "수정된 내용입니다."}]},
                    {"type": "paragraph"}
                ]
            }
            self.client.patch(f"/api/notes/{note_id}/edit/", json=data)

            
