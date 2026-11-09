import logging
import os

import firebase_admin

from firebase_admin import app_check
from firebase_admin.exceptions import FirebaseError

from jwt.exceptions import PyJWTError

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from starlette.concurrency import run_in_threadpool

from backend import ControllerRegistry

import asyncio
import math
import time

from collections import deque


logger = logging.getLogger("clinplain")


class AfterCareApplication:
    """
    Main FastAPI application for ClinPlain.

    Features:
    - OCR and medical document analysis
    - FHIR normalization
    - Patient-friendly explanations
    - Teach-Back
    - Firebase App Check verification
    - Google Cloud Run deployment
    """

    def __init__(self):

        self.app = FastAPI(
            title="ClinPlain API",
            description=(
                "AI-assisted medical document understanding "
                "with OCR, FHIR normalization, "
                "patient-friendly explanations, and Teach-Back."
            ),
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
        )

        # Enable App Check automatically on Cloud Run.
        # Local development keeps App Check disabled.
        default_enforcement = (
            "true" if os.getenv("K_SERVICE") else "false"
        )

        self.app_check_enabled = (
            os.getenv(
                "APP_CHECK_ENFORCE",
                default_enforcement,
            ).strip().lower() == "true"
        )

        self.firebase_app = None

        if self.app_check_enabled:
            self.firebase_app = self.initialize_firebase()

        # Register rate limiting first.
        self.configure_rate_limiting()

        # App Check runs before rate limiting.
        self.configure_app_check()

        # CORS remains the outermost middleware.
        self.configure_cors()

        # Initialize and register existing controllers.
        self.controller_registry = ControllerRegistry(
            self.app
        )

        self.controller_registry.register()

        # Register health endpoints.
        self.register_health_routes()

    def initialize_firebase(self):
        """
        Initialize Firebase Admin SDK using
        Application Default Credentials.

        On Cloud Run, credentials are obtained from
        the Cloud Run service account automatically.
        """

        try:
            return firebase_admin.get_app()

        except ValueError:
            return firebase_admin.initialize_app(
                options={
                    "projectId": os.environ[
                        "GOOGLE_CLOUD_PROJECT"
                    ]
                }
            )

    def configure_app_check(self) -> None:
        """
        Verify Firebase App Check tokens for /api/*.

        OPTIONS requests are allowed for CORS preflight.

        Health and documentation endpoints remain
        outside this middleware's protected path.
        """

        @self.app.middleware("http")
        async def verify_app_check(
            request: Request,
            call_next,
        ):

            if (
                not self.app_check_enabled
                or request.method == "OPTIONS"
                or not request.url.path.startswith("/api/")
            ):
                return await call_next(request)

            token = request.headers.get(
                "X-Firebase-AppCheck",
                "",
            )

            if not token:
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Missing Firebase App Check token."
                    },
                )

            try:
                claims = await run_in_threadpool(
                    app_check.verify_token,
                    token,
                    app=self.firebase_app,
                )

                # Restrict access to the registered
                # ClinPlain Firebase Web App.
                expected_app_id = (
                    "1:123313351627:"
                    "web:d6e044033bfe1d7338244e"
                )

                if claims.get("sub") != expected_app_id:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": "Unrecognized Firebase application."
                        },
                    )

            except (ValueError, PyJWTError):
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Invalid Firebase App Check token."
                    },
                )

            except FirebaseError:
                logger.exception(
                    "Firebase App Check verification service error"
                )

                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "App Check verification unavailable."
                    },
                )

            except Exception:
                logger.exception(
                    "Unexpected App Check verification error"
                )

                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "App Check verification unavailable."
                    },
                )

            return await call_next(request)

    def configure_cors(self) -> None:
        """
        Allow local Angular development and
        the configured Firebase Hosting frontend.
        """

        allowed_origins = [
            "http://localhost:4200",
            "http://127.0.0.1:4200",
        ]

        frontend_origin = os.getenv(
            "FRONTEND_ORIGIN",
            "",
        ).strip().rstrip("/")

        if frontend_origin:
            allowed_origins.append(frontend_origin)

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=False,
            allow_methods=[
                "GET",
                "POST",
                "OPTIONS",
            ],
            allow_headers=[
                "*",
            ],
        )

    def register_health_routes(self) -> None:
        """
        Lightweight health endpoints.
        """

        @self.app.get(
            "/",
            tags=["Health"],
        )
        async def root():
            return {
                "status": "success",
                "application": "ClinPlain",
                "version": "1.0.0",
            }

        @self.app.get(
            "/health",
            tags=["Health"],
        )
        async def health():
            return {
                "status": "healthy",
                "service": "clinplain-api",
            }

    def configure_rate_limiting(self) -> None:
        """
        Simple in-memory rate limiting for the
        ClinPlain hackathon demo.

        Limits:
            All POST /api/*:
                30 requests / 10 minutes
                120 requests / 24 hours

            POST /api/documents/analyze:
                6 requests / 10 minutes
                30 requests / 24 hours

        Notes:
            - Counters are shared within one Python process.
            - Counters reset when the container restarts.
            - This is not a distributed or persistent limiter.
        """

        # Time windows in seconds.
        short_window = 10 * 60
        daily_window = 24 * 60 * 60

        # Global limits for all API POST requests.
        global_short_limit = 30
        global_daily_limit = 120

        # Additional limits for full document analysis.
        analysis_short_limit = 6
        analysis_daily_limit = 30

        # In-memory request histories.
        global_requests = deque()
        analysis_requests = deque()

        # Protect counters against concurrent requests.
        lock = asyncio.Lock()

        def cleanup_requests(history, now):
            """
            Remove timestamps outside the 24-hour window.
            """

            while (
                history
                and now - history[0] >= daily_window
            ):
                history.popleft()

        def calculate_retry_after(
            history,
            now,
            short_limit,
            daily_limit,
        ) -> int:
            """
            Return seconds until the request is allowed.

            Returns 0 when the request is within limits.
            """

            if len(history) >= daily_limit:
                return max(
                    1,
                    math.ceil(
                        daily_window - (now - history[0])
                    ),
                )

            recent_requests = [
                timestamp
                for timestamp in history
                if now - timestamp < short_window
            ]

            if len(recent_requests) >= short_limit:
                return max(
                    1,
                    math.ceil(
                        short_window
                        - (now - recent_requests[0])
                    ),
                )

            return 0

        @self.app.middleware("http")
        async def rate_limit_middleware(
            request: Request,
            call_next,
        ):

            # Only count POST requests to application APIs.
            # Health, Swagger, GET and CORS preflight
            # requests are not counted.
            if (
                request.method != "POST"
                or not request.url.path.startswith("/api/")
            ):
                return await call_next(request)

            is_analysis = (
                request.url.path
                == "/api/documents/analyze"
            )

            now = time.monotonic()

            async with lock:

                cleanup_requests(
                    global_requests,
                    now,
                )

                cleanup_requests(
                    analysis_requests,
                    now,
                )

                global_retry_after = calculate_retry_after(
                    global_requests,
                    now,
                    global_short_limit,
                    global_daily_limit,
                )

                analysis_retry_after = 0

                if is_analysis:
                    analysis_retry_after = (
                        calculate_retry_after(
                            analysis_requests,
                            now,
                            analysis_short_limit,
                            analysis_daily_limit,
                        )
                    )

                retry_after = max(
                    global_retry_after,
                    analysis_retry_after,
                )

                if retry_after > 0:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": (
                                "API rate limit exceeded. "
                                "Please try again later."
                            )
                        },
                        headers={
                            "Retry-After": str(retry_after)
                        },
                    )

                # Reserve a request slot.
                global_requests.append(now)

                if is_analysis:
                    analysis_requests.append(now)

            return await call_next(request)
# ASGI entry point for Uvicorn and Cloud Run.
app = AfterCareApplication().app