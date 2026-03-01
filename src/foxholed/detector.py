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
    method: str = "template"


class PositionDetector:
    """Detects the player's map position from a minimap screenshot."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._templates: dict[str, np.ndarray] = {}
        self._load_templates()

    @property
    def template_count(self) -> int:
        """Number of loaded templates."""
        return len(self._templates)

    def reload_templates(self) -> None:
        """Reload templates from disk."""
        self._templates.clear()
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
            log.debug("Empty frame, skipping detection")
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        log.debug("Converted frame to grayscale (%dx%d)", gray.shape[1], gray.shape[0])

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
            log.info("No templates loaded, skipping template matching")
            return None

        best_score = 0.0
        best_name = ""
        best_loc: tuple[int, int] = (0, 0)
        best_template_shape: tuple[int, int] = (0, 0)
        scales = [0.75, 0.85, 1.0, 1.15, 1.25]

        for name, template in self._templates.items():
            for scale in scales:
                if scale == 1.0:
                    scaled = template
                else:
                    new_w = max(1, int(template.shape[1] * scale))
                    new_h = max(1, int(template.shape[0] * scale))
                    scaled = cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_AREA)

                # Skip if template is larger than the frame
                if scaled.shape[0] > gray.shape[0] or scaled.shape[1] > gray.shape[1]:
                    continue

                result = cv2.matchTemplate(gray, scaled, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)

                if max_val > best_score:
                    best_score = max_val
                    best_name = name
                    best_loc = max_loc
                    best_template_shape = (scaled.shape[1], scaled.shape[0])

            log.debug("Template %r best score: %.3f", name, best_score)

        log.info(
            "Best template match: %r with score %.1f%% (threshold %.1f%%)",
            best_name or "(none)",
            best_score * 100,
            self.config.match_confidence_threshold * 100,
        )

        if best_score >= self.config.match_confidence_threshold and best_name:
            if best_name in REGION_BY_NAME:
                frame_h, frame_w = gray.shape[:2]
                template_w, template_h = best_template_shape
                grid_x = (best_loc[0] + template_w / 2) / frame_w - 0.5
                grid_y = (best_loc[1] + template_h / 2) / frame_h - 0.5
                return Position(
                    region_name=best_name,
                    grid_x=grid_x,
                    grid_y=grid_y,
                    confidence=best_score,
                    method="template",
                )
            log.info("Best match %r not in known regions, discarding", best_name)

        return None

    def _ocr_coordinates(self, gray: np.ndarray) -> Position | None:
        """Attempt to read coordinate text from the minimap via OCR.

        Returns:
            Position if coordinates are successfully parsed, otherwise None.
        """
        try:
            import pytesseract
        except ImportError:
            log.info("pytesseract not available, skipping OCR fallback")
            return None

        log.info("Attempting OCR fallback")
        try:
            # Pre-process for better OCR
            _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            text = pytesseract.image_to_string(thresh, config="--psm 7")
            text = text.strip()

            if not text:
                log.info("OCR returned no text")
                return None

            log.info("OCR text: %r", text)

            # Try to parse region name from OCR output
            for region_name in REGION_BY_NAME:
                if region_name.lower() in text.lower():
                    log.info("OCR matched region: %s", region_name)
                    return Position(
                        region_name=region_name,
                        grid_x=0.0,
                        grid_y=0.0,
                        confidence=0.5,
                        method="ocr",
                    )

            log.info("OCR text did not match any known region")
        except Exception:
            log.debug("OCR failed", exc_info=True)

        return None
