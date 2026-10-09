# Discrete point extraction

## What the detector measures

Point mode finds local concentrations of pixels in the selected color family and reports the center of each accepted concentration. It is intended for circular, square, diamond, or similarly compact markers. It does not infer points hidden behind other markers or reconstruct the source table.

Black markers are supported. Because axes and text are also dark, crop to the plot frame accurately and exclude any in-frame legend or annotation before accepting black-point results.

## Separate data markers from non-data graphics

Before extraction, identify colored content inside the plot frame that is not data:

- legend markers and fitting-line samples;
- colored text, arrows, labels, or panel annotations;
- a fitted curve using the same color as the markers.

Pass each rectangular legend or annotation area as `--exclude-region x1,y1,x2,y2`, using image pixel coordinates. A fitting curve normally has lower local pixel density than a compact marker; increase `--point-min-pixels` if line pixels are being mistaken for points.

## Threshold controls

- `--point-window`: odd-sized local window in pixels. Start near the visible marker diameter.
- `--point-min-pixels`: minimum selected-color pixels inside the window. Raise it to reject thin lines and noise; lower it for small or hollow markers.
- `--point-min-distance`: minimum center-to-center pixel distance. Set near half to one marker diameter. Larger values suppress duplicates but can merge close points.

Change one threshold at a time and compare both point count and spatial distribution with the image.

## Dense and overlapping regions

At raster resolution, touching markers may become one colored cluster and markers underneath other markers are unavailable. Treat the result as digitized visible centers, not the original raw observations. Report likely undercounting where the plot is visibly crowded.

## Workbook chart

Use an XY scatter chart with markers and no connecting line. Preserve series color and, when practical, marker shape. Put different colors in separate X/Y column pairs and label them using the visible legend.
