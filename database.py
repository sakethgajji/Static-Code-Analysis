import sqlite3
import os

DB_NAME = 'analysis.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Report (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            date TEXT NOT NULL,
            quality_score REAL NOT NULL,
            errors INTEGER NOT NULL,
            warnings INTEGER NOT NULL,
            security_issues INTEGER NOT NULL,
            status TEXT NOT NULL,
            pdf_report_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_report(project_name, date, quality_score, errors, warnings, security_issues, status, pdf_report_path=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Report (project_name, date, quality_score, errors, warnings, security_issues, status, pdf_report_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (project_name, date, quality_score, errors, warnings, security_issues, status, pdf_report_path))
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    return report_id

def get_all_reports():
    conn = get_db_connection()
    reports = conn.execute('SELECT * FROM Report ORDER BY report_id DESC').fetchall()
    conn.close()
    return [dict(row) for row in reports]

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
