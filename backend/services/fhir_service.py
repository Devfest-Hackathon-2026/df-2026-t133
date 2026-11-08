import json
import re
from pathlib import Path

from jsonschema import Draft6Validator

from ..models.fhir_schemas import (
    FHIRNormalizeRequest,
    FactContext,
)
from ..models.medical_schemas import MedicalFact


class FHIRService:
    SUPPORTED_TYPES = (
        "Immunization",
        "DiagnosticReport",
    )

    def __init__(self):
        schema_path = (
            Path(__file__).resolve().parents[1]
            / "schemas"
            / "fhir_r4"
            / "fhir.schema.json"
        )

        if not schema_path.exists():
            raise FileNotFoundError(
                f"FHIR R4 schema not found: {schema_path}"
            )

        with schema_path.open("r", encoding="utf-8") as f:
            schema = json.load(f)

        # Validate the schema definition itself.
        Draft6Validator.check_schema(schema)

        self.validators = {}

        for resource_type in self.SUPPORTED_TYPES:
            resource_schema = {
                "$schema": "http://json-schema.org/draft-06/schema#",
                "$ref": f"#/definitions/{resource_type}",
                "definitions": schema["definitions"],
            }

            self.validators[resource_type] = Draft6Validator(
                resource_schema
            )

    @staticmethod
    def _valid_patient_reference(
        reference: str | None,
    ) -> bool:
        """
        Validate the syntax of a relative Patient reference.

        This does not verify that the Patient exists
        on a FHIR server.
        """
        if not reference:
            return False

        return bool(
            re.fullmatch(
                r"Patient/[A-Za-z0-9.-]{1,64}",
                reference,
            )
        )

    def _validate_resource(
        self,
        resource: dict,
    ) -> bool:
        """
        Validate a resource against HL7 FHIR R4 JSON Schema.
        """
        resource_type = resource.get("resourceType")

        validator = self.validators.get(resource_type)

        if validator is None:
            return False

        return validator.is_valid(resource)

    def _map_immunization(
        self,
        fact: MedicalFact,
        context: FactContext | None,
    ) -> tuple[dict | None, list[str]]:
        """
        Map an immunization fact to a FHIR R4
        Immunization resource.
        """
        missing = []

        patient = (
            context.patient_reference
            if context else None
        )

        event_date = (
            context.occurrence_date
            if context else None
        )

        event_status = (
            context.immunization_status
            if context else None
        )

        vaccine_name = (fact.value or "").strip()

        # Validate patient reference.
        if not self._valid_patient_reference(patient):
            missing.append(
                "Verified Patient reference is required."
            )

        # Require a confirmed immunization date.
        if event_date is None:
            missing.append(
                "Confirmed immunization date is required."
            )

        # This MVP mapper only supports completed events.
        if event_status != "completed":
            missing.append(
                "Confirmed completed immunization status "
                "is required."
            )

        if not vaccine_name:
            missing.append(
                "Vaccine name is missing."
            )

        if missing:
            return None, missing

        resource = {
            "resourceType": "Immunization",
            "status": "completed",
            "vaccineCode": {
                "text": vaccine_name,
            },
            "patient": {
                "reference": patient,
            },
            "occurrenceDateTime": event_date.isoformat(),
        }

        return resource, []

    def _map_diagnostic_report(
        self,
        fact: MedicalFact,
        context: FactContext | None,
    ) -> tuple[dict | None, list[str]]:
        """
        Map a diagnostic report fact to a FHIR R4
        DiagnosticReport resource.
        """
        missing = []

        patient = (
            context.patient_reference
            if context else None
        )

        report_status = (
            context.report_status
            if context else None
        )

        report_name = (fact.value or "").strip()

        if not self._valid_patient_reference(patient):
            missing.append(
                "Verified Patient reference is required."
            )

        if report_status is None:
            missing.append(
                "Confirmed report status is required."
            )

        if not report_name:
            missing.append(
                "Report name is missing."
            )

        if missing:
            return None, missing

        resource = {
            "resourceType": "DiagnosticReport",
            "status": report_status,
            "code": {
                "text": report_name,
            },
            "subject": {
                "reference": patient,
            },
        }

        return resource, []

    def normalize(
        self,
        request: FHIRNormalizeRequest,
    ) -> dict:
        """
        Normalize extracted medical facts into:

        - mapped: Valid FHIR R4 resources.
        - pending_review: Missing or unverified information.
        - unmapped: Clinical statements without a mapper.
        """
        mapped = []
        pending_review = []
        unmapped = []

        # Build a lookup for verified fact contexts.
        contexts = {
            (
                context.page_index,
                context.source_line_index,
            ): context
            for context in request.contexts
        }

        for page in request.pages:
            for fact in page.facts:

                source = {
                    "page_index": page.page_index,
                    "source_line_index": fact.source_line_index,
                    "source_quote": fact.source_quote,
                }

                entry = {
                    "source": source,
                    "fhir_hint": fact.fhir_hint,
                    "label": fact.label,
                    "value": fact.value,
                }

                # Step 1: Preserve general clinical context.
                if fact.fhir_hint == "Other":
                    unmapped.append({
                        **entry,
                        "reason": (
                            "Clinical context retained "
                            "without FHIR mapping."
                        ),
                    })
                    continue

                # Step 2: Respect extraction review flags.
                if fact.needs_review:
                    pending_review.append({
                        **entry,
                        "reasons": [
                            "Medical extraction requires review."
                        ],
                    })
                    continue

                # Step 3: Check supported resource types.
                if fact.fhir_hint not in self.SUPPORTED_TYPES:
                    unmapped.append({
                        **entry,
                        "reason": (
                            "FHIR resource mapper "
                            "not implemented."
                        ),
                    })
                    continue

                # Step 4: Find additional verified context.
                context_key = (
                    page.page_index,
                    fact.source_line_index,
                )

                context = contexts.get(context_key)

                # Step 5: Build the FHIR resource.
                if fact.fhir_hint == "Immunization":
                    resource, missing = self._map_immunization(
                        fact,
                        context,
                    )

                elif fact.fhir_hint == "DiagnosticReport":
                    resource, missing = self._map_diagnostic_report(
                        fact,
                        context,
                    )

                else:
                    continue

                # Step 6: Check required information.
                if missing:
                    pending_review.append({
                        **entry,
                        "reasons": missing,
                    })
                    continue

                # Step 7: Validate FHIR R4 JSON structure.
                if not self._validate_resource(resource):
                    pending_review.append({
                        **entry,
                        "reasons": [
                            "FHIR R4 JSON Schema validation failed."
                        ],
                    })
                    continue

                # Step 8: Save successfully mapped resource.
                mapped.append({
                    **entry,
                    "resource": resource,
                    "validation": "fhir_r4_json_schema",
                })

        return {
            "status": "success",
            "fhir_version": "4.0.1",
            "mapped": mapped,
            "pending_review": pending_review,
            "unmapped": unmapped,
        }