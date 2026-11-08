from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import ControllerRegistry


class AfterCareApplication:

    def __init__(self):
        self.app = FastAPI(
            title="ClinPlain API",
            description=(
                "AI-powered medical document understanding "
                "and patient-friendly explanations."
            ),
            version="1.0.0",
        )

        # Allow Angular frontend to access FastAPI.
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:4200",
                "http://127.0.0.1:4200",
            ],
            allow_credentials=False,
            allow_methods=[
                "GET",
                "POST",
                "OPTIONS",
            ],
            allow_headers=["*"],
        )

        # Initialize and register controllers.
        self.controller_registry = ControllerRegistry(self.app)

        for controller in self.controller_registry.controllers:
            self.app.include_router(
                controller.get_router()
            )

        # Health check.
        @self.app.get("/", tags=["Health"])
        async def health_check():
            return {
                "status": "success",
                "application": "ClinPlain",
                "message": "ClinPlain API is running.",
            }


app = AfterCareApplication().app