# Microservices Architecture with FastAPI
## IT4020 - Modern Topics in IT | Lab 3

---

## Project Structure

```
microservices-fastapi/
├── requirements.txt
├── README.md
├── student-service/
│   ├── main.py          ← FastAPI app (port 8001)
│   ├── models.py        ← Pydantic models
│   ├── service.py       ← Business logic
│   └── data_service.py  ← Mock data layer
├── course-service/      ← Activity 1
│   ├── main.py          ← FastAPI app (port 8002)
│   ├── models.py
│   ├── service.py
│   └── data_service.py
└── gateway/
    └── main.py          ← API Gateway (port 8000)
                            + JWT Auth  (Activity 2)
                            + Logging   (Activity 3)
                            + Error Handling (Activity 4)
```

---

## Setup

```bash
# 1. Create & activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
```

---

## Running the Services

Open **3 separate terminals**, each with the venv activated:

### Terminal 1 — Student Service (port 8001)
```bash
cd student-service
uvicorn main:app --reload --port 8001
```

### Terminal 2 — Course Service (port 8002)
```bash
cd course-service
uvicorn main:app --reload --port 8002
```

### Terminal 3 — API Gateway (port 8000)
```bash
cd gateway
uvicorn main:app --reload --port 8000
```

---

## API Docs (Swagger UI)

| Service         | URL                          |
|-----------------|------------------------------|
| API Gateway     | http://localhost:8000/docs   |
| Student Service | http://localhost:8001/docs   |
| Course Service  | http://localhost:8002/docs   |

---

## Architecture

```
Client
  │
  ▼
API Gateway  (port 8000)
  ├── /gateway/students  ──▶  Student Service (port 8001)
  └── /gateway/courses   ──▶  Course Service  (port 8002)
```

---

## Authentication (Activity 2)

All `/gateway/*` routes require a **Bearer JWT token**.

### Step 1 — Login
```
POST http://localhost:8000/auth/login
Body (form-data):
  username = admin
  password = admin123
```

### Step 2 — Use the token
Add header to all requests:
```
Authorization: Bearer <your_token>
```

**Available users:**
| Username | Password   | Role    |
|----------|------------|---------|
| admin    | admin123   | admin   |
| student  | student123 | student |

In Swagger UI, click the **Authorize 🔒** button and paste the token.

---

## Testing CRUD via Gateway

### Students
```
GET    /gateway/students          → Get all students
GET    /gateway/students/1        → Get student by ID
POST   /gateway/students          → Create student
PUT    /gateway/students/1        → Update student
DELETE /gateway/students/1        → Delete student
```

Sample POST body:
```json
{
  "name": "Alice Williams",
  "age": 23,
  "email": "alice@example.com",
  "course": "Data Science"
}
```

### Courses
```
GET    /gateway/courses           → Get all courses
GET    /gateway/courses/1         → Get course by ID
POST   /gateway/courses           → Create course
PUT    /gateway/courses/1         → Update course
DELETE /gateway/courses/1         → Delete course
```

Sample POST body:
```json
{
  "title": "Cybersecurity",
  "code": "CY501",
  "credits": 3,
  "instructor": "Dr. Smith",
  "description": "Introduction to cybersecurity"
}
```

---

## Activities Implemented

| Activity | Description                        | Location          |
|----------|------------------------------------|-------------------|
| 1        | Course Microservice (port 8002)    | `course-service/` |
| 2        | JWT Authentication                 | `gateway/main.py` |
| 3        | Request Logging Middleware         | `gateway/main.py` |
| 4        | Enhanced Error Handling            | `gateway/main.py` |
