import os
from dotenv import load_dotenv
from locust import HttpUser, between, task
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")  # 미리 발급받은 토큰
class NoteUser(HttpUser):
    wait_time = between(0.1, 0.5)
    def on_start(self):
        # Locust 요청 헤더에 미리 발급받은 토큰 넣기
        self.client.headers = {
            "Authorization": f"Bearer {SUPABASE_ACCESS_TOKEN}",
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





