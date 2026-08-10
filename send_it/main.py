import json
import os
from datetime import datetime
from typing import Optional

import aiofiles
from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlmodel import Session, select

load_dotenv()

from auth import (
    create_access_token,
    get_current_admin,
    get_current_manager,
    get_current_user,
    hash_password,
    verify_password,
)
from database.session import create_db_and_tables, get_session
from models.document import Document
from models.user import User, UserCreate, UserResponse
from services.weather import get_weather


# ==========================================================
# FASTAPI APPLICATION
# ==========================================================

app = FastAPI(
    title="SendIt API",
    version="1.0.0",
    description="Document Management & Weather Enrichment API",
)


# ==========================================================
# CONFIGURATION
# ==========================================================

UPLOAD_DIR = "uploads"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True,
)

MAX_FILE_SIZE = int(
    os.getenv(
        "MAX_UPLOAD_SIZE",
        5 * 1024 * 1024,
    )
)

ALLOWED_EXTENSIONS = [
    ext.strip()
    for ext in os.getenv(
        "ALLOWED_EXTENSIONS",
        ".pdf,.jpg,.jpeg,.png,.docx",
    ).split(",")
]


# ==========================================================
# RATE LIMITER
# ==========================================================

limiter = Limiter(
    key_func=get_remote_address
)

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


# ==========================================================
# STARTUP
# ==========================================================

@app.on_event("startup")
def startup():
    if os.getenv("TESTING") != "1":
        create_db_and_tables()


# ==========================================================
# HOME
# ==========================================================

@app.get("/")
def home():
    return {
        "message": "Welcome to SendIt API",
        "status": "Running",
    }


# ==========================================================
# WEBHOOK
# ==========================================================

router = APIRouter()


@router.post("/webhooks/register")
def register_webhook(url: str):
    return {
        "message": "Webhook registered",
        "url": url,
    }


app.include_router(router)


# ==========================================================
# REGISTER
# ==========================================================

@app.post(
    "/register",
    response_model=UserResponse,
)
def register(
    user: UserCreate,
    session: Session = Depends(get_session),
):
    existing = session.exec(
        select(User).where(
            User.username == user.username
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Username already exists",
        )

    email_exists = session.exec(
        select(User).where(
            User.email == user.email
        )
    ).first()

    if email_exists:
        raise HTTPException(
            status_code=400,
            detail="Email already exists",
        )

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(
            user.password
        ),
        full_name=user.full_name,
        role=user.role,
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    return new_user


# ==========================================================
# LOGIN
# ==========================================================

@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    user = session.exec(
        select(User).where(
            User.username == form_data.username
        )
    ).first()

    if (
        not user
        or not verify_password(
            form_data.password,
            user.hashed_password,
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    user.last_login = datetime.utcnow()

    session.add(user)
    session.commit()

    token = create_access_token(
        {"sub": user.username}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


# ==========================================================
# CURRENT USER
# ==========================================================

@app.get(
    "/me",
    response_model=UserResponse,
)
def me(
    current_user: User = Depends(
        get_current_user
    ),
):
    return current_user


# ==========================================================
# LIST USERS - ADMIN ONLY
# ==========================================================

@app.get(
    "/users",
    response_model=list[UserResponse],
)
def list_users(
    current_user: User = Depends(
        get_current_admin
    ),
    session: Session = Depends(
        get_session
    ),
):
    return session.exec(
        select(User)
    ).all()


# ==========================================================
# DISABLE USER - ADMIN ONLY
# ==========================================================

@app.put(
    "/users/{user_id}/disable"
)
def disable_user(
    user_id: int,
    current_user: User = Depends(
        get_current_admin
    ),
    session: Session = Depends(
        get_session
    ),
):
    user = session.get(
        User,
        user_id,
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    user.is_active = False

    session.add(user)
    session.commit()

    return {
        "message": "User disabled successfully",
    }


# ==========================================================
# DOCUMENT UPLOAD
# ==========================================================

@app.post(
    "/documents/upload"
)
@limiter.limit("10/hour")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    city: str = Form(...),
    country: str = Form("Kenya"),
    description: Optional[str] = Form(None),
    current_user: User = Depends(
        get_current_user
    ),
    session: Session = Depends(
        get_session
    ),
):
    file_extension = os.path.splitext(
        file.filename
    )[1].lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Allowed file types: "
                f"{', '.join(ALLOWED_EXTENSIONS)}"
            ),
        )

    contents = await file.read()

    file_size = len(contents)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File exceeds maximum upload size.",
        )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    safe_filename = (
        f"{timestamp}_"
        f"{current_user.id}_"
        f"{file.filename.replace(' ', '_')}"
    )

    file_path = os.path.join(
        UPLOAD_DIR,
        safe_filename,
    )

    async with aiofiles.open(
        file_path,
        "wb",
    ) as f:
        await f.write(contents)

    document = Document(
        filename=safe_filename,
        original_filename=file.filename,
        file_size=file_size,
        file_type=(
            file.content_type
            or "application/octet-stream"
        ),
        city=city,
        country=country,
        description=description,
        uploader_id=current_user.id,
        file_path=file_path,
        status="processing",
    )

    session.add(document)
    session.commit()
    session.refresh(document)

    try:
        weather = await get_weather(
            city,
            country,
        )

        if weather:
            document.weather_data = json.dumps(
                weather
            )

            document.weather_fetched_at = (
                datetime.utcnow()
            )

            document.status = "enriched"

            session.add(document)
            session.commit()

    except Exception as e:
        print(e)

        document.status = "uploaded"

        session.add(document)
        session.commit()

    return {
        "message": "Document uploaded successfully",
        "document_id": document.id,
        "status": document.status,
    }


# ==========================================================
# LIST DOCUMENTS
# ==========================================================

@app.get("/documents")
@limiter.limit("30/minute")
def list_documents(
    request: Request,
    status: Optional[str] = None,
    city: Optional[str] = None,
    current_user: User = Depends(
        get_current_user
    ),
    session: Session = Depends(
        get_session
    ),
):
    query = select(Document)

    if current_user.role not in [
        "admin",
        "manager",
    ]:
        query = query.where(
            Document.uploader_id
            == current_user.id
        )

    if status:
        query = query.where(
            Document.status == status
        )

    if city:
        query = query.where(
            Document.city == city
        )

    return session.exec(query).all()



# ==========================================================
# SEARCH DOCUMENTS
# ==========================================================

@app.get("/documents/search")
def search_documents(
    keyword: str,
    session: Session = Depends(
        get_session
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    query = select(Document).where(
        Document.uploader_id
        == current_user.id,
        Document.filename.contains(
            keyword
        ),
    )

    return session.exec(query).all()



# ==========================================================
# GET ONE DOCUMENT
# ==========================================================

@app.get(
    "/documents/{document_id}"
)
@limiter.limit("30/minute")
def get_document(
    request: Request,
    document_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    session: Session = Depends(
        get_session
    ),
):
    document = session.get(
        Document,
        document_id,
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if (
        current_user.role
        not in ["admin", "manager"]
        and document.uploader_id
        != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    return document



# ==========================================================
# DELETE DOCUMENT
# ==========================================================

@app.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    document = session.exec(
        select(Document).where(
            Document.id == document_id,
            Document.uploader_id == current_user.id,
        )
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if (
        document.file_path
        and os.path.exists(document.file_path)
    ):
        os.remove(document.file_path)

    session.delete(document)
    session.commit()

    return {
        "message": "Document deleted successfully",
    }


# ==========================================================
# MANUAL WEATHER ENRICHMENT
# ==========================================================

@app.post(
    "/documents/{document_id}/enrich"
)
@limiter.limit("5/minute")
async def enrich_document(
    request: Request,
    document_id: int,
    current_user: User = Depends(
        get_current_manager
    ),
    session: Session = Depends(
        get_session
    ),
):
    document = session.get(
        Document,
        document_id,
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    weather = await get_weather(
        document.city,
        document.country,
    )

    if weather:
        document.weather_data = json.dumps(
            weather
        )

        document.weather_fetched_at = (
            datetime.utcnow()
        )

        document.status = "enriched"

        session.add(document)
        session.commit()

        return {
            "message": "Document enriched successfully",
            "weather": weather,
        }

    document.status = "failed"

    session.add(document)
    session.commit()

    raise HTTPException(
        status_code=500,
        detail="Weather enrichment failed",
    )


# ==========================================================
# DOCUMENT WEATHER
# ==========================================================

@app.get(
    "/documents/{document_id}/weather"
)
@limiter.limit("10/minute")
def get_document_weather(
    request: Request,
    document_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    session: Session = Depends(
        get_session
    ),
):
    document = session.get(
        Document,
        document_id,
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if (
        current_user.role
        not in ["admin", "manager"]
        and document.uploader_id
        != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    if not document.weather_data:
        raise HTTPException(
            status_code=404,
            detail="No weather data available",
        )

    return {
        "document_id": document.id,
        "city": document.city,
        "country": document.country,
        "weather": json.loads(
            document.weather_data
        ),
    }