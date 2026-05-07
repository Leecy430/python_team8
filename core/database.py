"""
[database.py]
SQLite DB의 연결·테이블 생성·헬퍼 함수를 모두 이 파일에서 관리한다.
모든 모듈(samsung_health, inbody, nutrition 등)은 이 파일을 import해서 DB에 접근한다.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("db/user.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS steps_daily (
        date        TEXT PRIMARY KEY,
        count       INTEGER,
        distance_m  REAL,
        calorie     REAL
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS steps_binning (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        date        TEXT,
        slot        INTEGER,
        time_label  TEXT,
        count       INTEGER,
        distance_m  REAL,
        calorie     REAL,
        speed       REAL,
        UNIQUE(date, slot)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sleep (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        date              TEXT,
        start_time        TEXT,
        end_time          TEXT,
        duration_min      REAL,
        sleep_score       REAL,
        efficiency        REAL,
        physical_recovery REAL,
        mental_recovery   REAL,
        total_rem_min     REAL
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS heart_rate (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        datetime  TEXT,
        bpm       INTEGER,
        bpm_min   INTEGER,
        bpm_max   INTEGER,
        tag       TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inbody (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        measured_at        TEXT,
        weight_kg          REAL,
        skeletal_muscle_kg REAL,
        body_fat_kg        REAL,
        body_fat_pct       REAL,
        bmi                REAL,
        arm_r_kg           REAL,
        arm_l_kg           REAL,
        leg_r_kg           REAL,
        leg_l_kg           REAL,
        trunk_kg           REAL,
        bmr_kcal           INTEGER
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS schedule (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        day_of_week INTEGER,   -- 0=월 1=화 2=수 3=목 4=금
        start_time  TEXT,
        end_time    TEXT,
        subject     TEXT,
        professor   TEXT,
        classroom   TEXT
    )""")

    # 식단 기록
    cur.execute("""
    CREATE TABLE IF NOT EXISTS meals (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        eaten_at    TEXT,
        food_name   TEXT,
        kcal        REAL,
        protein_g   REAL,
        carb_g      REAL,
        fat_g       REAL,
        image_path  TEXT
    )""")

    # 운동 기록
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exercises (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        done_at      TEXT,
        name         TEXT,
        met          REAL,
        duration_min REAL,
        kcal_burned  REAL
    )""")

    # 위치 설정 (집/학교/알바 시간대)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS location_settings (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT,   -- '집' | '학교' | '알바'
        address    TEXT,
        lat        REAL,
        lon        REAL,
        start_time TEXT,   -- '09:00'
        end_time   TEXT    -- '18:00'
    )""")

    conn.commit()
    conn.close()
    print("✅ DB 초기화 완료")

if __name__ == "__main__":
    init_db()