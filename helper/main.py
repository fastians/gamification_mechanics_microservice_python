from fastapi import FastAPI, Request, Response
import httpx
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configure CORS as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the service URLs
SERVICES = {
    "auth": "http://localhost:8001",
    "quest_catalog": "http://localhost:8002",
    "quest_processing": "http://localhost:8003",
}


@app.middleware("http")
async def proxy_requests(request: Request, call_next):
    path = request.url.path
    method = request.method.lower()

    # Handle preflight CORS requests
    if method == "options":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
            },
            content="",
        )

    # Determine which service to route to based on the path
    if (
        path.startswith("/signup")
        or path.startswith("/login")
        or path.startswith("/users")
        or path.startswith("/add-diamonds")
        or path.startswith("/add-gold")
    ):
        target_url = SERVICES["auth"] + path
    elif path.startswith("/quests") or path.startswith("/rewards"):
        target_url = SERVICES["quest_catalog"] + path
    elif (
        path.startswith("/assign-quest")
        or path.startswith("/user-quests")
        or path.startswith("/complete-quest")
        or path.startswith("/track-sign-in")
        or path.startswith("/claim-quest")
    ):
        target_url = SERVICES["quest_processing"] + path
    else:
        return Response(content="Not Found", status_code=404)

    async with httpx.AsyncClient() as client:
        try:
            if method == "get":
                resp = await client.get(
                    target_url,
                    params=request.query_params,
                    headers=dict(request.headers),
                )
            elif method == "post":
                body = await request.body()
                resp = await client.post(
                    target_url, content=body, headers=dict(request.headers)
                )
            elif method == "put":
                body = await request.body()
                resp = await client.put(
                    target_url, content=body, headers=dict(request.headers)
                )
            elif method == "delete":
                resp = await client.delete(target_url, headers=dict(request.headers))
            else:
                return Response(content="Method Not Allowed", status_code=405)
        except httpx.RequestError as e:
            return Response(content=str(e), status_code=500)

    # Prepare the response to return to the client
    return Response(
        content=resp.content, status_code=resp.status_code, headers=resp.headers
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
