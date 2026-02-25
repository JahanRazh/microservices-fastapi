# gateway/main.py
# Includes: Activity 1 (Course Service), Activity 2 (JWT Auth),
#           Activity 3 (Request Logging), Activity 4 (Enhanced Error Handling)

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Any, Optional
import httpx
import logging
import time

# ─────────────────────────────────────────────
# Logging Setup (Activity 3)
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("api-gateway")

# ─────────────────────────────────────────────
# JWT Auth Config (Activity 2)
# ─────────────────────────────────────────────
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Mock users database
FAKE_USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin123"),
        "role": "admin",
    },
    "student": {
        "username": "student",
        "hashed_password": pwd_context.hash("student123"),
        "role": "student",
    },
}

# ─────────────────────────────────────────────
# App & Service Registry
# ─────────────────────────────────────────────
app = FastAPI(
    title="API Gateway",
    version="1.0.0",
    description="Central API Gateway with JWT Auth, Logging & Error Handling",
)

SERVICES = {
    "student": "http://localhost:8001",
    "course":  "http://localhost:8002",
}

# ─────────────────────────────────────────────
# Activity 3: Request Logging Middleware
# ─────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"➡  {request.method} {request.url.path}  |  client={request.client.host}")

    response = await call_next(request)

    duration = round((time.time() - start_time) * 1000, 2)
    logger.info(
        f"⬅  {request.method} {request.url.path}  |  "
        f"status={response.status_code}  |  {duration}ms"
    )
    return response

# ─────────────────────────────────────────────
# Activity 2: JWT Helper Functions
# ─────────────────────────────────────────────
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = FAKE_USERS.get(username)
    if user is None:
        raise credentials_exception
    return user

# ─────────────────────────────────────────────
# Activity 4: Enhanced Request Forwarding
# ─────────────────────────────────────────────
async def forward_request(service: str, path: str, method: str, **kwargs) -> Any:
    """Forward a request to the appropriate microservice with enhanced error handling."""

    if service not in SERVICES:
        logger.error(f"Unknown service requested: '{service}'")
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Service not found",
                "requested_service": service,
                "available_services": list(SERVICES.keys()),
            },
        )

    url = f"{SERVICES[service]}{path}"
    logger.info(f"Forwarding {method} → {url}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            method_map = {
                "GET":    client.get,
                "POST":   client.post,
                "PUT":    client.put,
                "DELETE": client.delete,
                "PATCH":  client.patch,
            }
            if method not in method_map:
                raise HTTPException(
                    status_code=405,
                    detail={"error": "Method not allowed", "method": method},
                )

            response = await method_map[method](url, **kwargs)

            # Propagate upstream HTTP errors with detail
            if response.status_code >= 400:
                try:
                    detail = response.json()
                except Exception:
                    detail = {"error": response.text or "Upstream error"}
                raise HTTPException(status_code=response.status_code, detail=detail)

            if response.status_code == 204 or not response.text:
                return JSONResponse(content=None, status_code=response.status_code)

            return JSONResponse(content=response.json(), status_code=response.status_code)

        except httpx.ConnectError:
            logger.error(f"Service '{service}' is unreachable at {url}")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Service unavailable",
                    "service": service,
                    "hint": f"Make sure the {service} service is running.",
                },
            )
        except httpx.TimeoutException:
            logger.error(f"Request to '{service}' timed out")
            raise HTTPException(
                status_code=504,
                detail={"error": "Gateway timeout", "service": service},
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(f"Unexpected error forwarding to '{service}'")
            raise HTTPException(
                status_code=500,
                detail={"error": "Internal gateway error", "message": str(exc)},
            )

# ─────────────────────────────────────────────
# Auth Routes (Activity 2)
# ─────────────────────────────────────────────
@app.post("/auth/login", tags=["Authentication"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and receive a JWT access token.
    
    Default credentials:
    - admin / admin123
    - student / student123
    """
    user = FAKE_USERS.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info(f"User '{user['username']}' logged in successfully")
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me", tags=["Authentication"])
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {"username": current_user["username"], "role": current_user["role"]}

# ─────────────────────────────────────────────
# Root
# ─────────────────────────────────────────────
@app.get("/", tags=["Gateway"])
def read_root():
    return {
        "message": "API Gateway is running",
        "available_services": list(SERVICES.keys()),
        "docs": "/docs",
    }

# ─────────────────────────────────────────────
# Student Service Routes (secured with JWT)
# ─────────────────────────────────────────────
@app.get("/gateway/students", tags=["Students"])
async def get_all_students(current_user: dict = Depends(get_current_user)):
    """Get all students through gateway (requires authentication)"""
    return await forward_request("student", "/api/students", "GET")


@app.get("/gateway/students/{student_id}", tags=["Students"])
async def get_student(student_id: int, current_user: dict = Depends(get_current_user)):
    """Get a student by ID through gateway (requires authentication)"""
    return await forward_request("student", f"/api/students/{student_id}", "GET")


@app.post("/gateway/students", tags=["Students"])
async def create_student(request: Request, current_user: dict = Depends(get_current_user)):
    """Create a new student through gateway (requires authentication)"""
    body = await request.json()
    return await forward_request("student", "/api/students", "POST", json=body)


@app.put("/gateway/students/{student_id}", tags=["Students"])
async def update_student(student_id: int, request: Request,
                         current_user: dict = Depends(get_current_user)):
    """Update a student through gateway (requires authentication)"""
    body = await request.json()
    return await forward_request("student", f"/api/students/{student_id}", "PUT", json=body)


@app.delete("/gateway/students/{student_id}", tags=["Students"])
async def delete_student(student_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a student through gateway (requires authentication)"""
    return await forward_request("student", f"/api/students/{student_id}", "DELETE")

# ─────────────────────────────────────────────
# Course Service Routes — Activity 1 (secured)
# ─────────────────────────────────────────────
@app.get("/gateway/courses", tags=["Courses"])
async def get_all_courses(current_user: dict = Depends(get_current_user)):
    """Get all courses through gateway (requires authentication)"""
    return await forward_request("course", "/api/courses", "GET")


@app.get("/gateway/courses/{course_id}", tags=["Courses"])
async def get_course(course_id: int, current_user: dict = Depends(get_current_user)):
    """Get a course by ID through gateway (requires authentication)"""
    return await forward_request("course", f"/api/courses/{course_id}", "GET")


@app.post("/gateway/courses", tags=["Courses"])
async def create_course(request: Request, current_user: dict = Depends(get_current_user)):
    """Create a new course through gateway (requires authentication)"""
    body = await request.json()
    return await forward_request("course", "/api/courses", "POST", json=body)


@app.put("/gateway/courses/{course_id}", tags=["Courses"])
async def update_course(course_id: int, request: Request,
                        current_user: dict = Depends(get_current_user)):
    """Update a course through gateway (requires authentication)"""
    body = await request.json()
    return await forward_request("course", f"/api/courses/{course_id}", "PUT", json=body)


@app.delete("/gateway/courses/{course_id}", tags=["Courses"])
async def delete_course(course_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a course through gateway (requires authentication)"""
    return await forward_request("course", f"/api/courses/{course_id}", "DELETE")
