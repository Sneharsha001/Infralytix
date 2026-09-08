import io
import sys
import uuid
import zipfile
import httpx

BASE_URL = "http://localhost:8000"
PROXY_URL = "http://localhost:5173"

def run_suite():
    results = []

    def report(name, success, detail=""):
        status_str = "PASS" if success else "FAIL"
        print(f"[{status_str}] {name} - {detail}")
        results.append((name, success, detail))

    client = httpx.Client(base_url=BASE_URL, timeout=60.0)

    # 1. Root and Discovery
    try:
        r = client.get("/")
        report("GET /", r.status_code == 200, f"Status: {r.status_code}")
    except Exception as e:
        report("GET /", False, str(e))

    # 2. Health check
    try:
        r = client.get("/api/v1/health")
        report("GET /api/v1/health", r.status_code == 200 and r.json().get("status") == "healthy", f"Status: {r.status_code}")
    except Exception as e:
        report("GET /api/v1/health", False, str(e))

    # 3. Readiness check
    try:
        r = client.get("/api/v1/health/ready")
        report("GET /api/v1/health/ready", r.status_code == 200, f"Status: {r.status_code}")
    except Exception as e:
        report("GET /api/v1/health/ready", False, str(e))

    # 4. Auth - Registration
    unique_suffix = str(uuid.uuid4())[:8]
    test_email = f"testuser_{unique_suffix}@infralytix.com"
    test_password = "SecurePassword123!"
    try:
        r = client.post("/api/v1/auth/register", json={
            "email": test_email,
            "password": test_password,
            "name": f"Test User {unique_suffix}"
        })
        report("POST /api/v1/auth/register", r.status_code == 201, f"Status: {r.status_code}")
    except Exception as e:
        report("POST /api/v1/auth/register", False, str(e))

    # 5. Auth - Login
    access_token = None
    refresh_token = None
    try:
        r = client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        if r.status_code == 200:
            data = r.json()
            access_token = data.get("access_token")
            # Refresh token might be in cookies or response body
            refresh_token = r.cookies.get("refresh_token") or data.get("refresh_token")
            report("POST /api/v1/auth/login", True, "Access token received")
        else:
            report("POST /api/v1/auth/login", False, f"Status: {r.status_code} {r.text}")
    except Exception as e:
        report("POST /api/v1/auth/login", False, str(e))

    auth_headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}

    # 6. Auth - Get Me
    try:
        r = client.get("/api/v1/auth/me", headers=auth_headers)
        report("GET /api/v1/auth/me", r.status_code == 200 and r.json().get("email") == test_email, f"Status: {r.status_code}")
    except Exception as e:
        report("GET /api/v1/auth/me", False, str(e))

    # 7. Auth - Token Refresh
    try:
        refresh_payload = {"refresh_token": refresh_token} if refresh_token else {}
        r = client.post("/api/v1/auth/refresh", json=refresh_payload)
        report("POST /api/v1/auth/refresh", r.status_code in (200, 204), f"Status: {r.status_code}")
    except Exception as e:
        report("POST /api/v1/auth/refresh", False, str(e))

    # 8. Projects - Create Project
    project_id = None
    try:
        r = client.post("/api/v1/projects", headers=auth_headers, json={
            "name": f"Test Project {unique_suffix}",
            "description": "Integration test project"
        })
        if r.status_code == 201:
            project_id = r.json().get("id")
            report("POST /api/v1/projects", True, f"Created project_id={project_id}")
        else:
            report("POST /api/v1/projects", False, f"Status: {r.status_code} {r.text}")
    except Exception as e:
        report("POST /api/v1/projects", False, str(e))

    # 9. Projects - List Projects
    try:
        r = client.get("/api/v1/projects", headers=auth_headers)
        report("GET /api/v1/projects", r.status_code == 200 and isinstance(r.json(), list), f"Status: {r.status_code}")
    except Exception as e:
        report("GET /api/v1/projects", False, str(e))

    # 10. Projects - Get Project by ID
    if project_id:
        try:
            r = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
            report(f"GET /api/v1/projects/{{id}}", r.status_code == 200, f"Status: {r.status_code}")
        except Exception as e:
            report(f"GET /api/v1/projects/{{id}}", False, str(e))

        # 11. Projects - Patch Project
        try:
            r = client.patch(f"/api/v1/projects/{project_id}", headers=auth_headers, json={
                "description": "Updated project description"
            })
            report(f"PATCH /api/v1/projects/{{id}}", r.status_code == 200, f"Status: {r.status_code}")
        except Exception as e:
            report(f"PATCH /api/v1/projects/{{id}}", False, str(e))

        # 12. Projects - Upload zip repo
        try:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("app.py", "from fastapi import FastAPI\napp = FastAPI()\n")
                z.writestr("requirements.txt", "fastapi>=0.100.0\nuvicorn>=0.20.0\n")
            buf.seek(0)
            files = {"file": ("repo.zip", buf.getvalue(), "application/zip")}
            r = client.post(f"/api/v1/projects/{project_id}/upload", headers=auth_headers, files=files)
            report(f"POST /api/v1/projects/{{id}}/upload", r.status_code in (200, 201), f"Status: {r.status_code}")
        except Exception as e:
            report(f"POST /api/v1/projects/{{id}}/upload", False, str(e))

        # 13. Projects - Analyze (AI Agents)
        try:
            r = client.post(f"/api/v1/projects/{project_id}/analyze", headers=auth_headers)
            report(f"POST /api/v1/projects/{{id}}/analyze", r.status_code in (200, 201, 202), f"Status: {r.status_code}")
        except Exception as e:
            report(f"POST /api/v1/projects/{{id}}/analyze", False, str(e))

        # 14. Projects - Get Analysis Results
        try:
            r = client.get(f"/api/v1/projects/{project_id}/analysis", headers=auth_headers)
            report(f"GET /api/v1/projects/{{id}}/analysis", r.status_code == 200, f"Status: {r.status_code}")
        except Exception as e:
            report(f"GET /api/v1/projects/{{id}}/analysis", False, str(e))

        # 15. Projects - Get Agent Runs
        try:
            r = client.get(f"/api/v1/projects/{project_id}/agent-runs", headers=auth_headers)
            report(f"GET /api/v1/projects/{{id}}/agent-runs", r.status_code == 200, f"Status: {r.status_code}")
        except Exception as e:
            report(f"GET /api/v1/projects/{{id}}/agent-runs", False, str(e))

    # 16. Cost - Direct /api/v1/cost/estimate
    try:
        r = client.post("/api/v1/cost/estimate", json={
            "vcpu": 2,
            "ram_gb": 4,
            "storage_gb": 50,
            "region": "us-east",
            "hours_per_month": 730
        })
        report("POST /api/v1/cost/estimate", r.status_code == 200, f"Status: {r.status_code}")
    except Exception as e:
        report("POST /api/v1/cost/estimate", False, str(e))

    # 17. Cost - /api/v1/cost-comparison (Alias)
    try:
        r = client.post("/api/v1/cost-comparison", json={
            "vcpu": 2,
            "ram_gb": 4,
            "storage_gb": 50,
            "region": "us-east",
            "hours_per_month": 730
        })
        report("POST /api/v1/cost-comparison", r.status_code == 200, f"Status: {r.status_code}")
    except Exception as e:
        report("POST /api/v1/cost-comparison", False, str(e))

    # 18. Workflows - Validate DAG
    try:
        r = client.post("/api/v1/workflows", json={
            "tasks": [
                {"id": "t1", "name": "Task 1", "category": "io_bound", "baseline_time_seconds": 60, "depends_on": []},
                {"id": "t2", "name": "Task 2", "category": "cpu_bound", "baseline_time_seconds": 120, "depends_on": ["t1"]}
            ]
        })
        report("POST /api/v1/workflows", r.status_code in (200, 201), f"Status: {r.status_code}")
    except Exception as e:
        report("POST /api/v1/workflows", False, str(e))

    # 19. Workflows - Optimize DAG
    try:
        r = client.post("/api/v1/workflows/optimize", json={
            "workflow": {
                "tasks": [
                    {"id": "t1", "name": "Task 1", "category": "io_bound", "baseline_time_seconds": 60, "baseline_vcpu": 2, "baseline_ram_gb": 4, "depends_on": []},
                    {"id": "t2", "name": "Task 2", "category": "cpu_bound", "baseline_time_seconds": 120, "baseline_vcpu": 4, "baseline_ram_gb": 8, "depends_on": ["t1"]}
                ]
            },
            "region": "us-east"
        })
        report("POST /api/v1/workflows/optimize", r.status_code == 200, f"Status: {r.status_code}")
    except Exception as e:
        report("POST /api/v1/workflows/optimize", False, str(e))

    # 20. Vite Proxy Verification (/api/v1 via frontend port 5173)
    try:
        proxy_client = httpx.Client(base_url=PROXY_URL, timeout=10.0)
        r = proxy_client.get("/api/v1/health")
        report("VITE PROXY GET /api/v1/health", r.status_code == 200, f"Proxied Status: {r.status_code}")
    except Exception as e:
        report("VITE PROXY GET /api/v1/health", False, str(e))

    # 21. Clean up project
    if project_id:
        try:
            r = client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)
            report(f"DELETE /api/v1/projects/{{id}}", r.status_code == 204, f"Status: {r.status_code}")
        except Exception as e:
            report(f"DELETE /api/v1/projects/{{id}}", False, str(e))

    # Summary
    total = len(results)
    passed = sum(1 for _, s, _ in results if s)
    failed = total - passed
    print("\n=======================================================")
    print(f"API TEST SUMMARY: {passed}/{total} PASSED, {failed} FAILED")
    print("=======================================================")
    return failed == 0

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)
