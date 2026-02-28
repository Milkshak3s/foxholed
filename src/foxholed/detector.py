"""Position detection via OpenCV template matching and Tesseract OCR."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from foxholed.config import Config
from foxholed.map_data import REGION_BY_NAME

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Position:
    """Detected player position on the Foxhole map."""

    region_name: str
    grid_x: float
    grid_y: float
    confidence: float


class PositionDetector:
    """Detects the player's map position from a minimap screenshot."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._templates: dict[str, np.ndarray] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load template images from the configured templates directory."""
        templates_dir = Path(self.config.templates_dir)
        if not templates_dir.is_dir():
            log.warning("Templates directory not found: %s", templates_dir)
            return

        for path in templates_dir.glob("*.png"):
            name = path.stem
            img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                self._templates[name] = img
                log.info("Loaded template: %s", name)

        log.info("Loaded %d templates", len(self._templates))

    def detect(self, frame: np.ndarray) -> Position | None:
        """Attempt to detect the player's position from a minimap frame.

        Args:
            frame: Minimap image as a BGR numpy array.

        Returns:
            Detected Position, or None if detection fails.
        """
        if frame is None or frame.size == 0:
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Try template matching against all loaded region templates
        best_match = self._match_templates(gray)
        if best_match is not None:
            return best_match

        # Fall back to OCR for coordinate text
        return self._ocr_coordinates(gray)

    def _match_templates(self, gray: np.ndarray) -> Position | None:
        """Run template matching against loaded templates.

        Returns:
            Best matching Position above the confidence threshold, or None.
        """
        if not self._templates:
            return None

        best_score = 0.0
        best_name = ""

        for name, template in self._templates.items():
            # Skip if template is larger than the frame
            if (
                template.shape[0] > gray.shape[0]
                or template.shape[1] > gray.shape[1]
            ):
                continue

            result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val > best_score:
                best_score = max_val
                best_name = name

        if best_score >= self.config.match_confidence_threshold and best_name:
            # Check if the template name matches a known region
            if best_name in REGION_BY_NAME:
                return Position(
                    region_name=best_name,
                    grid_x=0.0,
                    grid_y=0.0,
                    confidence=best_score,
                )

        return None

    def _ocr_coordinates(self, gray: np.ndarray) -> Position | None:
        """Attempt to read coordinate text from the minimap via OCR.

        Returns:
            Position if coordinates are successfully parsed, otherwise None.
        """
        try:
            import pytesseract
        except ImportError:
            log.debug("pytesseract not available for OCR fallback")
            return None

        try:
            # Pre-process for better OCR
            _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            text = pytesseract.image_to_string(thresh, config="--psm 7")
            text = text.strip()

            if not text:
                return None

            # Try to parse region name from OCR output
            for region_name in REGION_BY_NAME:
                if region_name.lower() in text.lower():
                    return Position(
                        region_name=region_name,
                        grid_x=0.0,
                        grid_y=0.0,
                        confidence=0.5,
                    )
        except Exception:
            log.debug("OCR failed", exc_info=True)

        return None
