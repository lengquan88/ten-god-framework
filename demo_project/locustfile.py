"""
Locust load testing file for TenGod API
"""
from locust import HttpUser, task, between
import random
import json


class TenGodUser(HttpUser):
    """
    Simulates a user interacting with the TenGod API
    """
    wait_time = between(1, 3)
    
    def on_start(self):
        """Called when a user starts"""
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    @task(3)
    def calculate_bazi(self):
        """Calculate Bazi (Chinese fortune telling)"""
        payload = {
            "year": random.randint(1980, 2000),
            "month": random.randint(1, 12),
            "day": random.randint(1, 28),
            "hour": random.randint(0, 23),
            "minute": random.randint(0, 59),
            "gender": random.choice([1, 0]),
            "solar_calendar": True
        }
        self.client.post("/api/v1/bazi/calculate", json=payload, headers=self.headers)
    
    @task(2)
    def get_palace_info(self):
        """Get palace information"""
        palace_id = random.randint(1, 12)
        self.client.get(f"/api/v1/palace/{palace_id}", headers=self.headers)
    
    @task(2)
    def get_star_info(self):
        """Get star information"""
        star_id = random.randint(1, 100)
        self.client.get(f"/api/v1/star/{star_id}", headers=self.headers)
    
    @task(1)
    def get_combination_analysis(self):
        """Get combination analysis"""
        payload = {
            "star_ids": [random.randint(1, 50) for _ in range(random.randint(2, 4))],
            "analysis_type": random.choice(["compatibility", "interaction", "strength"])
        }
        self.client.post("/api/v1/analysis/combination", json=payload, headers=self.headers)
    
    @task(1)
    def health_check(self):
        """Health check endpoint"""
        self.client.get("/health")
