# PPSU_Assignment_Tracker

A Python automation project that logs into the **P P Savani University ERP**, extracts **subject-wise pending assignments** from the LMS, normalizes dates, and outputs structured JSON data for further consumption (widgets, dashboards, automation, etc.).

This project is designed to run **locally** as well as **automatically via GitHub Actions**.

---

## 🚀 Features

- Logs into PPSU ERP (ASP.NET WebForms based)
- Navigates LMS pages and extracts assignments
- Filters **pending assignments only**
- Normalizes date and time formats
- Generates machine-readable JSON outputs
- Designed for CI/CD execution (GitHub Actions)
- Structured logging for debugging and auditability

---

## 🧠 How It Works

1. Authenticate into the university ERP using credentials
2. Fetch LMS dashboard and subject pages
3. Extract assignment details:
   - Subject
   - Title
   - Due date & time
4. Normalize and structure the data
5. Write outputs as JSON files

---

## 🔐 Configuration

### Environment Variables
Create a `.env` file:

```env
ERP_USERNAME=your_username
ERP_PASSWORD=your_password
```
### Note
This project is intended for personal academic use only.