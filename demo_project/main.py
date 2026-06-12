#!/usr/bin/env python3
"""main.py — 应用入口 (比肩·架构协同)"""
import os
from src.auth_service import authenticate
from src.data_store import save_record
from src.report_generator import generate_report

def main():
    user = os.environ.get("USER", "anonymous")
    if not authenticate(user):
        print("Access denied")
        return
    record = {"user": user, "action": "login", "status": "ok"}
    save_record(record)
    report = generate_report([record])
    print(report)

if __name__ == "__main__":
    main()
