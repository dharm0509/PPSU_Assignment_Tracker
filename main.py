import requests
from bs4 import BeautifulSoup

LOGIN_URL = "https://erp.ppsu.ac.in/Login.aspx"

headers = {
    "User-Agent": "Mozilla/5.0"
}
session = requests.Session()

r = session.get(LOGIN_URL, headers=headers)
soup = BeautifulSoup(r.text, "html.parser")

hidden_fields = {}

for inp in soup.find_all("input", type="hidden"):
    if inp.get("name"):
        hidden_fields[inp["name"]] = inp.get("value", "")

payload = hidden_fields.copy()

payload.update({
    "rblRole": "Student",
    "txtUserName": "22se02ml077@ppsu.ac.in",
    "txtPassword": "Hamilton@44",
    "btnLogin": "Login"
})

resp = session.post(LOGIN_URL, headers=headers, data=payload)

if "StudentDashboard.aspx" in resp.text:
    print("✅ LOGIN SUCCESS")
elif "Validation of viewstate MAC failed" in resp.text:
    print("❌ VIEWSTATE BROKEN")
else:
    print("❌ LOGIN FAILED")

lms_url = "https://erp.ppsu.ac.in/StudentPanel/LMS/LMS_ContentStudentDashboard.aspx"

lms_resp = session.get(
    lms_url,
    headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://erp.ppsu.ac.in/StudentPanel/StudentDashboard.aspx"
    }
)

print(lms_resp.status_code)

from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import re

soup = BeautifulSoup(lms_resp.text, "html.parser")
subjects = []

for a in soup.select("a[href*='LMS_Content_SubjectWiseContentList.aspx']"):
    href = a["href"]
    qs = parse_qs(urlparse(href).query)

    raw_text = a.get_text(" ", strip=True)

    # Extract subject code + name
    match = re.search(r"[A-Z]{4}\d{4}\s*-\s*.+", raw_text)
    subject_name = match.group().strip() if match else raw_text

    subjects.append({
        "subject_id": qs.get("SubjectID", [""])[0],
        "academic_session_id": qs.get("AcademicSessionID", [""])[0],
        "semester": qs.get("Semester", [""])[0],
        "subject_name": subject_name
    })

for s in subjects:
    print(s)

def fetch_subject_page(session, subject):
    url = (
        "https://erp.ppsu.ac.in/StudentPanel/LMS/"
        "LMS_Content_SubjectWiseContentList.aspx?"
        f"SubjectID={subject['subject_id']}&"
        f"AcademicSessionID={subject['academic_session_id']}&"
        f"Semester={subject['semester']}"
    )

    resp = session.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://erp.ppsu.ac.in/StudentPanel/LMS/LMS_ContentStudentDashboard.aspx"
        }
    )

    return resp.text

subject_pages = {}

for subject in subjects:
    html = fetch_subject_page(session, subject)

    subject_pages[subject["subject_name"]] = html
    print(f"Fetched: {subject['subject_name']} | Size: {len(html)}")

from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

def extract_assignments_from_assignment_table(subject_name):
    html = subject_pages.get(subject_name)
    if not html:
        return []  # safety

    soup = BeautifulSoup(html, "html.parser")

    tables = soup.find_all("table", id="tblSubjectWiseContentDetails")

    assignment_table = None

    for table in tables:
        header_row = table.find("tr")
        if not header_row:
            continue

        ths = header_row.find_all("th")
        if len(ths) < 2:
            continue

        second_th_text = ths[1].get_text(strip=True)

        if second_th_text == "Assignment details":
            assignment_table = table
            break   # ✅ stop once found

    # ✅ NO ASSIGNMENTS CASE
    if assignment_table is None:
        return []   # return empty list instead of error

    assignments = []

    rows = assignment_table.find_all("tr")

    for row in rows[1:]:  # skip header
        tds = row.find_all("td")
        if len(tds) < 10:
            continue

        # 1️⃣ Title + ContentID
        title_link = tds[1].find("a")
        title = title_link.get_text(strip=True) if title_link else None

        content_id = None
        if title_link and title_link.has_attr("href"):
            qs = parse_qs(urlparse(title_link["href"]).query)
            content_id = qs.get("ContentID", [None])[0]

        # 2️⃣ Updated on
        updated_on = tds[3].get_text(" ", strip=True)

        # 3️⃣ Due date
        due_date = tds[4].get_text(" ", strip=True)

        # 4️⃣ Prepared by
        prepared_by = tds[5].get_text(strip=True)

        # 5️⃣ Submission status
        submission_status = tds[9].get_text(" ", strip=True)

        assignments.append({
            "subject_name": subject_name,
            "title": title,
            "content_id": content_id,
            "updated_on": updated_on,
            "due_date": due_date,
            "prepared_by": prepared_by,
            "submission_status": submission_status
        })

    return assignments

t =extract_assignments_from_assignment_table("SECE4060 - Artificial Inteligence of Things")
print(t)