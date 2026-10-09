#!/usr/bin/env python3
"""Digitize one colored curve or discrete marker series from a raster plot."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image


COLOR_RULES = {
    "black": lambda r, g, b: (r < 90) & (g < 90) & (b < 90),
    "red": lambda r, g, b: (r > 140) & (r - g > 30) & (r - b > 30),
    "green": lambda r, g, b: (g > 110) & (g - r > 25) & (g - b > 20),
    "blue": lambda r, g, b: (b > 120) & (b - r > 25) & (b - g > 20),
    "cyan": lambda r, g, b: (g > 110) & (b > 110) & (g - r > 25) & (b - r > 25),
    "magenta": lambda r, g, b: (r > 120) & (b > 120) & (r - g > 25) & (b - g > 25),
    "yellow": lambda r, g, b: (r > 130) & (g > 130) & (r - b > 25) & (g - b > 25),
    "auto": lambda r, g, b: (np.maximum.reduce([r, g, b]) > 120)
    & (np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b]) > 40),
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--metadata", type=Path)
    p.add_argument("--mode", choices=("curve", "points"), default="curve")
    p.add_argument("--x-left-value", type=float, required=True)
    p.add_argument("--x-right-value", type=float, required=True)
    p.add_argument("--y-top-value", type=float, required=True)
    p.add_argument("--y-bottom-value", type=float, required=True)
    p.add_argument("--x-left-px", type=int)
    p.add_argument("--x-right-px", type=int)
    p.add_argument("--y-top-px", type=int)
    p.add_argument("--y-bottom-px", type=int)
    p.add_argument("--x-step", type=float)
    p.add_argument("--x-scale", choices=("linear", "log"), default="linear")
    p.add_argument("--y-scale", choices=("linear", "log"), default="linear")
    p.add_argument("--curve-color", choices=tuple(COLOR_RULES), default="auto")
    p.add_argument("--exclude-region", action="append", default=[], metavar="X1,Y1,X2,Y2")
    p.add_argument("--point-window", type=int, default=9)
    p.add_argument("--point-min-pixels", type=int, default=22)
    p.add_argument("--point-min-distance", type=float, default=6.0)
    p.add_argument("--x-label", default="x")
    p.add_argument("--y-label", default="y")
    return p


def parse_region(text: str) -> tuple[int, int, int, int]:
    try:
        values = tuple(int(v.strip()) for v in text.split(","))
    except ValueError as exc:
        raise ValueError(f"Invalid --exclude-region: {text!r}") from exc
    if len(values) != 4:
        raise ValueError(f"Invalid --exclude-region: {text!r}")
    x1, y1, x2, y2 = values
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)


def window_sums(mask: np.ndarray, window: int) -> np.ndarray:
    if window < 3 or window % 2 == 0:
        raise ValueError("--point-window must be an odd integer of at least 3")
    radius = window // 2
    padded = np.pad(mask.astype(np.int32), radius, mode="constant")
    integral = np.pad(padded, ((1, 0), (1, 0)), mode="constant").cumsum(0).cumsum(1)
    return (
        integral[window:, window:]
        - integral[:-window, window:]
        - integral[window:, :-window]
        + integral[:-window, :-window]
    )


def detect_points(
    mask: np.ndarray,
    minimum_pixels: int,
    minimum_distance: float,
    window: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    density = window_sums(mask, window)
    candidates = np.argwhere(density >= minimum_pixels)
    if candidates.size == 0:
        raise ValueError("No marker centers detected; lower --point-min-pixels or check the color")
    scores = density[candidates[:, 0], candidates[:, 1]]
    order = np.argsort(scores)[::-1]
    chosen: list[tuple[float, float, int]] = []
    distance2 = minimum_distance * minimum_distance
    for index in order:
        y, x = (float(candidates[index, 0]), float(candidates[index, 1]))
        if all((x - old_x) ** 2 + (y - old_y) ** 2 >= distance2 for old_x, old_y, _ in chosen):
            chosen.append((x, y, int(scores[index])))
    chosen.sort(key=lambda item: (item[0], item[1]))
    return (
        np.asarray([item[0] for item in chosen]),
        np.asarray([item[1] for item in chosen]),
        np.asarray([item[2] for item in chosen]),
    )


def detect_frame(rgb: np.ndarray) -> tuple[int, int, int, int]:
    gray = rgb.astype(float).mean(axis=2)
    dark = gray < 70
    col_counts = dark.sum(axis=0)
    row_counts = dark.sum(axis=1)

    def strongest_pair(counts: np.ndarray, minimum_gap: int) -> tuple[int, int]:
        order = np.argsort(counts)[::-1]
        first = int(order[0])
        for candidate in order[1:]:
            candidate = int(candidate)
            if abs(candidate - first) >= minimum_gap:
                return tuple(sorted((first, candidate)))
        raise ValueError("Could not find two separated plot-frame lines")

    height, width = dark.shape
    x_left, x_right = strongest_pair(col_counts, max(20, width // 5))
    y_top, y_bottom = strongest_pair(row_counts, max(20, height // 5))
    if x_right - x_left < width * 0.2 or y_bottom - y_top < height * 0.2:
        raise ValueError("Detected frame is implausibly small; provide explicit pixel bounds")
    return x_left, x_right, y_top, y_bottom


def map_fraction(start: float, end: float, fraction: np.ndarray, scale: str) -> np.ndarray:
    if scale == "linear":
        return start + fraction * (end - start)
    if start <= 0 or end <= 0:
        raise ValueError("Logarithmic axis endpoints must be positive")
    return 10 ** (math.log10(start) + fraction * (math.log10(end) - math.log10(start)))


def main() -> None:
    args = parser().parse_args()
    rgb = np.asarray(Image.open(args.input).convert("RGB"), dtype=np.int16)
    height, width, _ = rgb.shape
    auto_bounds = detect_frame(rgb)
    x_left = args.x_left_px if args.x_left_px is not None else auto_bounds[0]
    x_right = args.x_right_px if args.x_right_px is not None else auto_bounds[1]
    y_top = args.y_top_px if args.y_top_px is not None else auto_bounds[2]
    y_bottom = args.y_bottom_px if args.y_bottom_px is not None else auto_bounds[3]
    if not (0 <= x_left < x_right < width and 0 <= y_top < y_bottom < height):
        raise ValueError("Plot-frame pixel bounds are outside the image or reversed")

    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    curve = COLOR_RULES[args.curve_color](r, g, b)
    roi = np.zeros(curve.shape, dtype=bool)
    roi[y_top : y_bottom + 1, x_left : x_right + 1] = True
    curve &= roi
    for region_text in args.exclude_region:
        ex1, ey1, ex2, ey2 = parse_region(region_text)
        curve[max(0, ey1) : min(height, ey2 + 1), max(0, ex1) : min(width, ex2 + 1)] = False

    if args.mode == "points":
        inset = args.point_window // 2 + 1
        curve[y_top : min(y_bottom + 1, y_top + inset), :] = False
        curve[max(y_top, y_bottom - inset + 1) : y_bottom + 1, :] = False
        curve[:, x_left : min(x_right + 1, x_left + inset)] = False
        curve[:, max(x_left, x_right - inset + 1) : x_right + 1] = False
        point_x, point_y, point_scores = detect_points(
            curve,
            args.point_min_pixels,
            args.point_min_distance,
            args.point_window,
        )
        inside = (
            (point_x >= x_left)
            & (point_x <= x_right)
            & (point_y >= y_top)
            & (point_y <= y_bottom)
        )
        point_x, point_y, point_scores = point_x[inside], point_y[inside], point_scores[inside]
        x_fraction = (point_x - x_left) / (x_right - x_left)
        y_fraction = (point_y - y_top) / (y_bottom - y_top)
        x_values = map_fraction(args.x_left_value, args.x_right_value, x_fraction, args.x_scale)
        y_values = map_fraction(args.y_top_value, args.y_bottom_value, y_fraction, args.y_scale)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([args.x_label, args.y_label, "pixel_x", "pixel_y", "marker_score"])
            for x_value, y_value, px, py, score in zip(
                x_values, y_values, point_x, point_y, point_scores
            ):
                writer.writerow([
                    f"{x_value:.12g}", f"{y_value:.12g}",
                    f"{px:.6f}", f"{py:.6f}", int(score),
                ])
        x_uncertainty = abs(args.x_right_value - args.x_left_value) / (x_right - x_left)
        y_uncertainty = abs(args.y_top_value - args.y_bottom_value) / (y_bottom - y_top)
        metadata = {
            "source_image": str(args.input.resolve()),
            "image_width_px": width,
            "image_height_px": height,
            "mode": "points",
            "frame": {"x_left": x_left, "x_right": x_right, "y_top": y_top, "y_bottom": y_bottom},
            "axis_values": {
                "x_left": args.x_left_value, "x_right": args.x_right_value,
                "y_top": args.y_top_value, "y_bottom": args.y_bottom_value,
            },
            "axis_scales": {"x": args.x_scale, "y": args.y_scale},
            "curve_color": args.curve_color,
            "detected_markers": int(len(x_values)),
            "point_settings": {
                "window": args.point_window,
                "minimum_pixels": args.point_min_pixels,
                "minimum_distance": args.point_min_distance,
                "excluded_regions": args.exclude_region,
            },
            "one_pixel_resolution": {"x": x_uncertainty, "y": y_uncertainty},
        }
        if args.metadata:
            args.metadata.parent.mkdir(parents=True, exist_ok=True)
            args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(metadata, ensure_ascii=False))
        return
    ys, xs = np.where(curve)
    if xs.size == 0:
        raise ValueError("No curve pixels detected; choose another color or explicit calibration")

    unique_x = np.unique(xs)
    curve_x = []
    curve_y = []
    for x in unique_x:
        column_y = ys[xs == x]
        curve_x.append(float(x))
        curve_y.append(float(np.median(column_y)))
    curve_x = np.asarray(curve_x)
    curve_y = np.asarray(curve_y)
    if len(curve_x) < max(20, int((x_right - x_left) * 0.1)):
        raise ValueError("Detected curve covers too little of the plot width")

    if args.x_step is None:
        sample_x = np.arange(x_left, x_right + 1, dtype=float)
        x_fraction = (sample_x - x_left) / (x_right - x_left)
        x_values = map_fraction(args.x_left_value, args.x_right_value, x_fraction, args.x_scale)
    else:
        if args.x_scale != "linear":
            raise ValueError("--x-step is supported only for linear X axes")
        direction = 1 if args.x_right_value >= args.x_left_value else -1
        step = abs(args.x_step) * direction
        count = int(round((args.x_right_value - args.x_left_value) / step))
        x_values = args.x_left_value + np.arange(count + 1) * step
        x_values[-1] = args.x_right_value
        x_fraction = (x_values - args.x_left_value) / (args.x_right_value - args.x_left_value)
        sample_x = x_left + x_fraction * (x_right - x_left)

    sample_y = np.interp(sample_x, curve_x, curve_y)
    y_fraction = (sample_y - y_top) / (y_bottom - y_top)
    y_values = map_fraction(args.y_top_value, args.y_bottom_value, y_fraction, args.y_scale)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([args.x_label, args.y_label, "pixel_x", "pixel_y"])
        for x_value, y_value, px, py in zip(x_values, y_values, sample_x, sample_y):
            writer.writerow([
                f"{x_value:.12g}",
                f"{y_value:.12g}",
                f"{px:.6f}",
                f"{py:.6f}",
            ])

    x_uncertainty = abs(args.x_right_value - args.x_left_value) / (x_right - x_left)
    y_uncertainty = abs(args.y_top_value - args.y_bottom_value) / (y_bottom - y_top)
    metadata = {
        "source_image": str(args.input.resolve()),
        "image_width_px": width,
        "image_height_px": height,
        "mode": "curve",
        "frame": {"x_left": x_left, "x_right": x_right, "y_top": y_top, "y_bottom": y_bottom},
        "axis_values": {
            "x_left": args.x_left_value,
            "x_right": args.x_right_value,
            "y_top": args.y_top_value,
            "y_bottom": args.y_bottom_value,
        },
        "axis_scales": {"x": args.x_scale, "y": args.y_scale},
        "curve_color": args.curve_color,
        "detected_curve_columns": int(len(curve_x)),
        "output_rows": int(len(x_values)),
        "one_pixel_resolution": {"x": x_uncertainty, "y": y_uncertainty},
    }
    if args.metadata:
        args.metadata.parent.mkdir(parents=True, exist_ok=True)
        args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == "__main__":
    main()
