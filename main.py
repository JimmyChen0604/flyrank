from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from db import get_db_connection, init_db

app = FastAPI(
    title="Task API",
    description="A small CRUD API for managing tasks.",
    version="1.0",
)

init_db()

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Return 400 instead of FastAPI's default 422 when the body is invalid."""
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request body: 'title' is required and must be a non-empty string."},
    )

@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

# ---------- Models ----------

class IndexResponse(BaseModel):
    name: str
    version: str
    endpoints: List[str]


class Task(BaseModel):
    id: int
    title: str
    done: bool


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


# ---------- In-memory store (create / update / delete until later stages) ----------

tasks_db: List[Task] = [
    Task(id=1, title="internship", done=False),
    Task(id=2, title="trends tracking", done=False),
    Task(id=3, title="dinner with family", done=False),
]


def find_task(task_id: int) -> Optional[Task]:
    """Return the task with the given id, or None if it doesn't exist."""
    for task in tasks_db:
        if task.id == task_id:
            return task
    return None


def next_id() -> int:
    """Return the smallest unused id, safe even after deletions."""
    return max((task.id for task in tasks_db), default=0) + 1


# ---------- Stage 1: root and health ----------

@app.get("/", response_model=IndexResponse, summary="Describe this API")
def index():
    """Return the API's name, version, and available endpoints."""
    return IndexResponse(
        name="Task API",
        version="1.0",
        endpoints=["/tasks"],
    )


@app.get("/health", summary="Health check")
def health():
    """Return 200 with a simple status, used to check the server is alive."""
    return {"status": "ok"}


# ---------- Stage 2: read ----------

@app.get("/tasks", response_model=List[Task], summary="List all tasks")
def list_tasks():
    """Return every task stored in the database."""
    conn = get_db_connection()
    rows = conn.execute("SELECT id, title, done FROM tasks").fetchall()
    conn.close()
    return [Task(id=row["id"], title=row["title"], done=bool(row["done"])) for row in rows]


@app.get("/tasks/{id}", response_model=Task, summary="Get one task")
def get_task(id: int):
    """Return a single task by id, or 404 if no task has that id."""
    conn = get_db_connection()
    row = conn.execute("SELECT id, title, done FROM tasks WHERE id = ?", (id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return Task(id=row["id"], title=row["title"], done=bool(row["done"]))


# ---------- Stage 3: create ----------

@app.post(
    "/tasks",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
)
def create_task(task_data: TaskCreate):
    """Create a new task with done=False and return it with status 201."""
    title = task_data.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty.")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (title, False))
    new_task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return Task(id=new_task_id, title=title, done=False)


# ---------- Stage 4: update and delete ----------

@app.put("/tasks/{id}", response_model=Task, summary="Update a task")
def update_task(id: int, task_data: TaskUpdate):
    """Update a task's title and/or done flag and return the updated task."""
    if task_data.title is None and task_data.done is None:
        raise HTTPException(status_code=400, detail="Request body cannot be empty.")

    task = find_task(id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {id} not found")

    if task_data.title is not None:
        title = task_data.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="Title cannot be empty.")
        task.title = title

    if task_data.done is not None:
        task.done = task_data.done

    return task


@app.delete(
    "/tasks/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
)
def delete_task(id: int):
    """Delete a task by id and return 204 with an empty body."""
    task = find_task(id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {id} not found")

    tasks_db.remove(task)
    return None
