MAN = """\
VECTOR-TRACE(1)                  User Commands                 VECTOR-TRACE(1)

NAME
    vector-trace - digitize a curve from an image of a 2D plot using Sobel
    edge detection

SYNOPSIS
    vector-trace extract IMAGE --xcal PX:VAL PX:VAL --ycal PY:VAL PY:VAL
                 [--seed X,Y] [--tol N] [--frame X0,Y0,X1,Y1] [--thr F]
                 [--xlog] [--ylog] [-o FILE]
    vector-trace --help | --man
    vector-trace extract --help | --man

    The same commands run as "python -m vector_trace ...".

DESCRIPTION
    vector-trace turns a picture of a plot (PNG, JPG, TIFF, BMP) into numbers.
    It finds the plot area, traces one curve, and converts pixel positions to
    data values using two reference points you give for each axis. The result
    is a CSV file plus an overlay image so you can check the trace by eye.

    The tool never reads tick labels. You tell it what two points on each axis
    are worth; it does the rest.

COMMANDS
    extract
        Trace one curve and write CSV and overlay PNG.

CALIBRATION
    Each axis needs two reference points, written PIXEL:VALUE.

        --xcal 193:0 1052:12       pixel columns 193 and 1052 are x = 0 and 12
        --ycal 653.5:0 88.5:140    pixel rows 653.5 and 88.5 are y = 0 and 140

    Pixel coordinates are pixel indices: origin at the top-left corner, x to
    the right, y downward, pixel centers at integers. Most image viewers
    (Paint, GIMP, ImageJ/Fiji) show this when you hover over a pixel. For
    --ycal the pixel is a row number.

    Grid lines and tick marks make good reference points. Pick points far
    apart: calibration error shrinks as the distance between them grows.

    For a logarithmic axis add --xlog and/or --ylog and give the real values
    (for example 10:10 and 546:100). Log-axis values must be greater than 0.
    The two pixels and the two values on an axis must each be different.

HOW THE CURVE IS FOUND
    The plot area is found automatically from the long, strong edges of the
    axis lines (Sobel gradient). If only a left and a bottom axis exist, the
    plot area is taken to run from them to the image edge. Use --frame if the
    guess is wrong. The search stays 3 pixels inside the axis lines.

    Without --seed:
        Sobel edges inside the plot area are thresholded (--thr) and the
        widest connected edge shape is traced. Fine for a single clean curve.

    With --seed X,Y:
        The tool takes the stroke color at the seed pixel and traces only the
        stroke of that color, so it can pick one curve out of several, ignore
        markers and annotations of other colors, and stay off grid lines.
        Anti-aliased edge pixels are kept. Small hidden spots, such as where a
        marker covers the line, are bridged. Strokes darker than the seed color
        (a black arrow across a navy curve) are rejected.

    Either way the result has one y value per image column: the middle of the
    traced stroke.

OPTIONS
    IMAGE               Input image.
    --xcal PX:VAL PX:VAL
                        Two x-axis reference points (required).
    --ycal PY:VAL PY:VAL
                        Two y-axis reference points (required).
    --seed X,Y          A pixel on the curve to trace, as image column, row.
                        Must be within 10 pixels of the curve. Enables color
                        tracing.
    --tol N             With --seed: color tolerance as an RGB distance
                        (default 40). Raise it if the trace breaks up along
                        the curve; lower it if it jumps to a similar-colored
                        neighbor.
    --frame X0,Y0,X1,Y1 Plot area in pixels, replacing auto-detection. The
                        corners are the inner edges of the axis lines.
    --thr F             Without --seed: edge threshold as a fraction of the
                        strongest gradient in the plot area (default 0.3).
    --xlog, --ylog      Logarithmic (base 10) x or y axis.
    -o, --output FILE   Output CSV path (default curve.csv).
    --help              Short usage summary.
    --man               This manual.

OUTPUT
    FILE (CSV)
        Header "series,x,y". One row per image column the curve covers,
        sorted by x, in data units. The series name is always "curve1".

    FILE with the extension replaced by .overlay.png
        The input image with the detected plot area in green and the traced
        curve in red. Always check this image before using the numbers.

EXIT STATUS
    0   Success.
    1   Error, with a message on standard error: unreadable image, invalid
        calibration, empty plot area, no curve found, or a seed that is not
        on a curve.
    2   Command-line usage error.

EXAMPLES
    Single clean curve, automatic selection:

        vector-trace extract fig.png --xcal 193:0 1052:12 \\
            --ycal 653.5:0 88.5:140 -o curve.csv

    One of several curves, chosen by clicking near it (column 908, row 335):

        vector-trace extract fig.png --xcal 193:0 1052:12 \\
            --ycal 653.5:0 88.5:140 --seed 908,335 -o blue.csv

    Logarithmic x axis, with the plot area given explicitly:

        vector-trace extract fig.png --xcal 253.5:10 546.5:100 --xlog \\
            --ycal 471.5:10 66.5:50 --frame 168,19,837,570 -o model.csv

LIMITATIONS
    - One curve per run. Run once per curve with a different --seed.
    - The curve must be a function of x (one y per x). Vertical or looping
      curves are not supported.
    - Dashed and dotted curves: only the dash touching the seed is traced.
    - Where one curve is drawn over another, the hidden part is missing.
    - Strokes very close to white (distance under 120 from white in RGB)
      cannot be seeded.
    - About 3 pixels at each end of a curve that meets an axis line are lost.
    - Automatic plot-area detection assumes the axis lines are the only long
      dark lines. A dark grid can fool it; pass --frame.
    - Raster images only. PDFs must be exported to an image first.
    - Accuracy on clean images is about one pixel; the result depends on how
      precisely the calibration points are placed.

SEE ALSO
    PRD.md in the project directory for the design and roadmap.
"""
