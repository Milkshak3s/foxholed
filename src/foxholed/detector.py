"""Position detection via orange triangle/arrow finding + template matching."""

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
    """Detects the player's map position by finding the orange marker
    on the full map screen, cropping around it, and template matching."""

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

    # ------------------------------------------------------------------
    # Main detection pipeline
    # ------------------------------------------------------------------

    def detect(self, frame: np.ndarray) -> Position | None:
        """Detect the player's position from a game window frame.

        Pipeline: find orange marker → crop around it → template match crop.

        Returns:
            Detected Position, or None if the marker isn't visible (map not open).
        """
        if frame is None or frame.size == 0:
            log.debug("Empty frame, skipping detection")
            return None

        # Step 1: Find the orange player marker
        marker = self.find_player_triangle(frame)
        if marker is None:
            log.debug("No player marker found (map likely not open)")
            return None

        cx, cy = marker
        log.info("Player marker found at (%d, %d)", cx, cy)

        # Step 2: Crop around the marker
        crop, (marker_in_crop_x, marker_in_crop_y) = self._crop_around(frame, cx, cy)

        # Step 3: Template match the crop
        gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return self._match_templates(gray_crop, marker_in_crop_x, marker_in_crop_y)

    # ------------------------------------------------------------------
    # Triangle / arrow detection
    # ------------------------------------------------------------------

    def find_player_triangle(self, frame: np.ndarray) -> tuple[int, int] | None:
        """Find the orange player marker on the map screen.

        Uses HSV color filtering to isolate orange pixels, then contour
        analysis to find a solid marker shape.

        Returns:
            (cx, cy) centroid of the marker, or None.
        """
        cfg = self.config
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        low = np.array([cfg.triangle_hue_low, cfg.triangle_sat_min, cfg.triangle_val_min])
        high = np.array([cfg.triangle_hue_high, 255, 255])
        mask = cv2.inRange(hsv, low, high)

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_candidate: tuple[int, int] | None = None
        best_solidity = 0.0

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < cfg.triangle_min_area or area > cfg.triangle_max_area:
                continue

            # Solidity = area / convex_hull_area
            # Solid filled shapes (arrow, triangle) have high solidity (>0.4)
            # Thin lines, text, noise have low solidity
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            if hull_area == 0:
                continue
            solidity = area / hull_area

            if solidity > 0.4 and solidity > best_solidity:
                M = cv2.moments(contour)
                if M["m00"] > 0:
                    best_solidity = solidity
                    best_candidate = (
                        int(M["m10"] / M["m00"]),
                        int(M["m01"] / M["m00"]),
                    )

        return best_candidate

    # ------------------------------------------------------------------
    # Crop extraction
    # ------------------------------------------------------------------

    def _crop_around(
        self, frame: np.ndarray, cx: int, cy: int
    ) -> tuple[np.ndarray, tuple[int, int]]:
        """Crop a region around the marker, clamped to frame bounds.

        Returns:
            (crop, (marker_x_in_crop, marker_y_in_crop))
        """
        r = self.config.crop_radius
        h, w = frame.shape[:2]
        x1 = max(0, cx - r)
        y1 = max(0, cy - r)
        x2 = min(w, cx + r)
        y2 = min(h, cy + r)
        crop = frame[y1:y2, x1:x2]
        return crop, (cx - x1, cy - y1)

    # ------------------------------------------------------------------
    # Template matching (on crop)
    # ------------------------------------------------------------------

    def _match_templates(
        self,
        gray: np.ndarray,
        marker_x: int,
        marker_y: int,
    ) -> Position | None:
        """Run multi-scale template matching on a cropped region.

        Grid offsets are computed from the marker's position relative to
        the matched template center, giving sub-region precision.
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
                template_w, template_h = best_template_shape
                # Marker position relative to template center → sub-region offset
                template_cx = best_loc[0] + template_w / 2
                template_cy = best_loc[1] + template_h / 2
                grid_x = (marker_x - template_cx) / template_w
                grid_y = (marker_y - template_cy) / template_h
                return Position(
                    region_name=best_name,
                    grid_x=grid_x,
                    grid_y=grid_y,
                    confidence=best_score,
                    method="template",
                )
            log.info("Best match %r not in known regions, discarding", best_name)

        return None
