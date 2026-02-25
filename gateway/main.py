# gateway/main.py
# Includes: Activity 1 (Course Service), Activity 2 (JWT Auth),
# Activity 3 (Request Logging), Activity 4 (Enhanced Error Handling)

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.responses import JSONResponse, Response
from auth import router as auth_router, get_current_user
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
                return Response(status_code=response.status_code)

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
# Auth Routes Inclusion
# ─────────────────────────────────────────────
app.include_router(auth_router)

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

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

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
