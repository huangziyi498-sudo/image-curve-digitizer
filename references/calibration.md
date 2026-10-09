# Curve image calibration

## Linear axes

For a plot frame bounded by `x_left`, `x_right`, `y_top`, and `y_bottom`, map pixels to values with:

```text
x = x_left_value + (pixel_x - x_left) / (x_right - x_left)
    * (x_right_value - x_left_value)

y = y_top_value + (pixel_y - y_top) / (y_bottom - y_top)
    * (y_bottom_value - y_top_value)
```

Image Y coordinates increase downward, so the second formula intentionally uses top and bottom values rather than assuming ascending values.

## Printed multipliers

Apply printed multipliers before passing axis endpoint values to the script.

Examples:

- X labels `-8` to `8` with `1E-1` mean `-0.8` to `0.8`.
- Y labels `-1` to `2` with `1E-4 A` mean `-1e-4` to `2e-4 A`.
- A Y label in `mA cm-2` is already a physical unit and should not be converted to amperes unless requested.

## Logarithmic axes

For log axes, interpolation occurs in log10 space. Endpoint values must be positive. Do not treat unevenly spaced tick labels as a linear scale.

## Frame detection

Automatic detection looks for the strongest dark vertical and horizontal lines. It works well for boxed plots on a light background. Verify the returned bounds against the visible plot rectangle.

Pass explicit pixel bounds when:

- the plot has no full rectangular border;
- grid lines are darker than the frame;
- multiple panels appear in one image;
- annotations or legends create stronger dark lines;
- automatic bounds do not align with the axis endpoints.

## Curve color selection

Use a named color when the curve is visibly red, blue, green, cyan, magenta, or yellow. Use `auto` only when there is one clearly saturated curve. If several colored curves are present, extract each color separately and name it from the legend.

## Quality checks

- Confirm the first and last extracted X values equal the calibrated endpoints or requested sampling range.
- Check at least three visually identifiable locations: an endpoint, a midpoint/inflection, and a peak or plateau.
- Replot extracted XY values and compare the shape with the source image.
- Treat line thickness as a vertical uncertainty of roughly half to one pixel unless the line is visibly thicker.
