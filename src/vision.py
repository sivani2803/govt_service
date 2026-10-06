"""Image analysis service boundary.

No computer-vision model is configured in this project. The default provider
therefore reports image metadata only and never invents a defect, severity, or
confidence score. A real provider can be supplied through the same interface.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from io import BytesIO
from typing import Any, Protocol

from PIL import Image, UnidentifiedImageError


@dataclass(frozen=True)
class VisionResult:
    status: str
    engine: str
    findings: tuple[str, ...]
    confidence_pct: float | None
    severity: str | None
    notes: tuple[str, ...]
    image_metadata: dict[str, int | str]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable result for storage or API responses."""
        return asdict(self)


class VisionProvider(Protocol):
    def analyze(self, image_bytes: bytes, *, service_code: str = "", service_name: str = "") -> VisionResult:
        """Analyze one image without raising for ordinary provider unavailability."""


class DemoVisionProvider:
    """Clearly labeled metadata-only demo; it does not claim to detect issues."""

    engine = "Demo Vision Analysis (metadata only; no computer-vision model)"

    def analyze(self, image_bytes: bytes, *, service_code: str = "", service_name: str = "") -> VisionResult:
        del service_code, service_name  # Category is not evidence of image contents.
        try:
            with Image.open(BytesIO(image_bytes)) as image:
                image_format = image.format or "Unknown"
                width, height = image.size
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValueError("The uploaded file is not a readable image.") from exc

        return VisionResult(
            status="demo_metadata_only",
            engine=self.engine,
            findings=(),
            confidence_pct=None,
            severity=None,
            notes=("No visual classification was performed. An officer must review the photo.",),
            image_metadata={"format": image_format, "width": width, "height": height},
        )


def get_vision_provider() -> VisionProvider:
    """Return the configured provider. Replace here when a real model is added."""
    return DemoVisionProvider()


def analyze_civic_image(
    image_bytes: bytes,
    service_code: str = "",
    service_name: str = "",
    *,
    provider: VisionProvider | None = None,
) -> dict[str, Any]:
    """Analyze a citizen image and return the stable, explicitly labeled schema."""
    if not isinstance(image_bytes, bytes) or not image_bytes:
        raise ValueError("An image is required for vision analysis.")
    selected_provider = provider or get_vision_provider()
    result = selected_provider.analyze(
        image_bytes, service_code=service_code, service_name=service_name
    )
    if not isinstance(result, VisionResult):
        raise TypeError("Vision providers must return a VisionResult.")
    return result.to_dict()
