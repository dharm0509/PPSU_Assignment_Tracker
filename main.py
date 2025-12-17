import os
import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import subprocess
from dotenv import load_dotenv
load_dotenv()

# Git commit logs and assignment json
def git_auto_commit():
    """
    Commits assignments.json and run_log.json if they changed.
    Intended for CI / GitHub Actions use.
    """
    try:
        subprocess.run(
            ["git", "add", "assignments.json", "run_log.json"],
            check=True
        )

        subprocess.run(
            ["git", "commit", "-m", "Auto-update assignments and logs"],
            check=True
        )

        subprocess.run(
            ["git", "push"],
            check=True
        )

        log("INFO", "git_commit", "Auto-commit and push successful")

    except subprocess.CalledProcessError as e:
        # No changes to commit is NOT an error
        log("INFO", "git_commit_skipped", "No changes to commit")

# Logs
def log(level, event, message, extra=None):
    entry = {
        "time": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "event": event,
        "message": message
    }
    if extra:
        entry["extra"] = extra
    _logs.append(entry)

# DATE NORMALIZATION
def normalize_datetime(date_str):
    """
    Converts '17-12-2025 12:00 PM' -> '2025-12-17T12:00:00'
    """
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y %I:%M %p")
        return dt.isoformat()
    except Exception:
        return None

# EXTRACT ASSIGNMENTS
def extract_assignments_from_assignment_table(subject_name):
    html = subject_pages.get(subject_name)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table", id="tblSubjectWiseContentDetails")

    assignment_table = None

    for table in tables:
        header_row = table.find("tr")
        if not header_row:
            continue

        ths = header_row.find_all("th")
        if len(ths) > 1 and ths[1].get_text(strip=True) == "Assignment details":
            assignment_table = table
            break

    if assignment_table is None:
        return []

    assignments = []

    rows = assignment_table.find_all("tr")[1:]

    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 10:
            continue

        title_link = tds[1].find("a")
        title = title_link.get_text(strip=True) if title_link else None

        content_id = None
        if title_link and title_link.has_attr("href"):
            qs = parse_qs(urlparse(title_link["href"]).query)
            content_id = qs.get("ContentID", [None])[0]

        updated_raw = tds[3].get_text(" ", strip=True)
        due_raw = tds[4].get_text(" ", strip=True)

        assignments.append({
            "subject_name": subject_name,
            "title": title,
            "content_id": content_id,
            "updated_on": normalize_datetime(updated_raw),
            "due_date": normalize_datetime(due_raw),
            "prepared_by": tds[5].get_text(strip=True),
            "submission_status": tds[9].get_text(" ", strip=True)
        })

    log("INFO", "assignments_extracted", "Assignments extracted", {
        "subject": subject_name,
        "count": len(assignments)
    })

    return assignments

def main():
    
    # ENVIRONMENT VARIABLES
    ERP_USERNAME = os.environ.get("ERP_USERNAME")
    ERP_PASSWORD = os.environ.get("ERP_PASSWORD")

    if not ERP_USERNAME or not ERP_PASSWORD:
        log("ERROR", "env_missing", "ERP_USERNAME or ERP_PASSWORD not set")
        raise RuntimeError("Missing ERP credentials in environment variables")

    # LOGIN
    log("INFO", "login_start", "Attempting ERP login")

    session = requests.Session()
    resp = session.get(LOGIN_URL)

    soup = BeautifulSoup(resp.text, "html.parser")

    payload = {
        inp["name"]: inp.get("value", "")
        for inp in soup.select("input[type=hidden]")
    }

    payload.update({
        "rblRole": "Student",
        "txtUserName": ERP_USERNAME,
        "txtPassword": ERP_PASSWORD,
        "btnLogin": "Login"
    })

    login_resp = session.post(LOGIN_URL, data=payload)

    if "StudentDashboard.aspx" not in login_resp.text:
        log("ERROR", "login_failed", "ERP login failed")
        raise RuntimeError("ERP login failed")

    log("INFO", "login_success", "ERP login successful")

    # FETCH SUBJECTS
    log("INFO", "fetch_subjects", "Fetching LMS dashboard")

    resp = session.get(LMS_DASHBOARD_URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    subjects = []

    for a in soup.find_all("a", href=True):
        if "LMS_Content_SubjectWiseContentList.aspx" not in a["href"]:
            continue

        qs = parse_qs(urlparse(a["href"]).query)

        raw_name = a.get_text(strip=True)
        clean = re.search(r"[A-Z]{4}\d{4}\s*-\s*.+", raw_name)
        subject_name = clean.group(0) if clean else raw_name

        subjects.append({
            "subject_name": subject_name,
            "subject_id": qs["SubjectID"][0],
            "academic_session_id": qs["AcademicSessionID"][0],
            "semester": qs["Semester"][0]
        })

    log("INFO", "subjects_found", f"{len(subjects)} subjects found")

    # FETCH SUBJECT PAGES
    global subject_pages
    subject_pages = {}

    for subject in subjects:
        resp = session.get(
            SUBJECT_CONTENT_URL,
            params={
                "SubjectID": subject["subject_id"],
                "AcademicSessionID": subject["academic_session_id"],
                "Semester": subject["semester"]
            }
        )
        subject_pages[subject["subject_name"]] = resp.text

    # COLLECT ALL ASSIGNMENTS
    all_assignments = []

    for subject in subjects:
        all_assignments.extend(
            extract_assignments_from_assignment_table(subject["subject_name"])
        )

    # BUILD JSON
    data = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "assignments": []
    }

    for a in all_assignments:
        if "submitted" in a["submission_status"].lower():
            continue

        data["assignments"].append({
            "subject": a["subject_name"],
            "title": a["title"],
            "due": a["due_date"],
            "content_id": a["content_id"]
        })

    data["count"] = len(data["assignments"])

    with open(ASSIGNMENTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    log("INFO", "json_written", "assignments.json written", {
        "count": data["count"]
    })

    # WRITE LOG FILE
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(_logs, f, indent=2)

    # git_auto_commit()

if __name__ == "__main__":
    # CONFIG
    LOGIN_URL = "https://erp.ppsu.ac.in/Login.aspx"
    LMS_DASHBOARD_URL = "https://erp.ppsu.ac.in/StudentPanel/LMS/LMS_ContentStudentDashboard.aspx"
    SUBJECT_CONTENT_URL = "https://erp.ppsu.ac.in/StudentPanel/LMS/LMS_Content_SubjectWiseContentList.aspx"

    ASSIGNMENTS_JSON = "assignments.json"
    LOG_FILE = "run_log.json"

    # STRUCTURED LOGGER (JSON)
    _logs = []

    try:
        main()
    except Exception as e:
        log("ERROR", "fatal", str(e))
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(_logs, f, indent=2)
        raise RuntimeError("it's shattered just like ur dreams!")
