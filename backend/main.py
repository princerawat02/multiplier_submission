from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from database import Base, SessionLocal, engine
from models import User, Website


SECRET_KEY = "change_this_to_a_long_random_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
NAVIGATION_TIMEOUT_MS = 20000
NETWORKIDLE_TIMEOUT_MS = 5000
RENDER_WAIT_MS = 1500

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

BASE_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Website Preview App API")

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PreviewRequest(BaseModel):
    url: str


class WebsiteResponse(BaseModel):
    id: int
    url: str
    screenshot_path: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    return user


def format_website_response(website: Website) -> WebsiteResponse:
    return WebsiteResponse(
        id=website.id,
        url=website.url,
        screenshot_path=f"/screenshots/{website.screenshot_path}",
        created_at=website.created_at,
    )


@app.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    name = payload.name.strip()
    email = payload.email.strip().lower()
    password = payload.password.strip()

    if not name or not password:
        raise HTTPException(status_code=400, detail="All fields are required")

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered")

    new_user = User(
        name=name,
        email=email,
        password=get_password_hash(password),
    )

    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email is already registered")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create user")

    return {"message": "Signup successful"}


@app.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    password = payload.password.strip()

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/preview", response_model=WebsiteResponse)
def generate_preview(
    payload: PreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    url = payload.url.strip()

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    file_name = f"{uuid4().hex}.png"
    screenshot_full_path = SCREENSHOTS_DIR / file_name

    def capture_with_chromium(extra_args: list[str] | None = None):
        launch_args = extra_args or []
        browser = p.chromium.launch(headless=True, args=launch_args, timeout=15000)
        try:
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                ignore_https_errors=True,
            )
            page = context.new_page()
            page.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
            page.set_default_timeout(NAVIGATION_TIMEOUT_MS)

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
                try:
                    page.wait_for_load_state("networkidle", timeout=NETWORKIDLE_TIMEOUT_MS)
                except PlaywrightTimeoutError:
                    # Continue with a partial render instead of blocking too long.
                    pass
            except PlaywrightTimeoutError:
                page.goto(url, wait_until="commit", timeout=NAVIGATION_TIMEOUT_MS)

            page.wait_for_timeout(RENDER_WAIT_MS)
            page.screenshot(path=str(screenshot_full_path), full_page=False)
            context.close()
        finally:
            browser.close()

    try:
        with sync_playwright() as p:
            try:
                capture_with_chromium()
            except Exception as first_error:
                # Retry with transport flags for websites that fail with HTTP/2 protocol errors.
                if "ERR_HTTP2_PROTOCOL_ERROR" in str(first_error):
                    capture_with_chromium(
                        [
                            "--disable-http2",
                            "--disable-quic",
                            "--disable-features=NetworkServiceInProcess",
                        ]
                    )
                else:
                    raise
    except PlaywrightTimeoutError:
        if screenshot_full_path.exists():
            screenshot_full_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Website loading timed out")
    except Exception as error:
        if screenshot_full_path.exists():
            screenshot_full_path.unlink(missing_ok=True)

        error_message = str(error)
        if "Executable doesn't exist" in error_message:
            raise HTTPException(
                status_code=500,
                detail="Playwright browser is not installed. Run: playwright install chromium",
            )

        raise HTTPException(
            status_code=400,
            detail=f"Failed to generate website preview: {error_message}",
        )

    new_website = Website(
        user_id=current_user.id,
        url=url,
        screenshot_path=file_name,
    )
    db.add(new_website)
    db.commit()
    db.refresh(new_website)

    return format_website_response(new_website)


@app.get("/websites", response_model=list[WebsiteResponse])
def get_websites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    websites = (
        db.query(Website)
        .filter(Website.user_id == current_user.id)
        .order_by(Website.created_at.desc())
        .all()
    )

    return [format_website_response(website) for website in websites]
