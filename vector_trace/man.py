MAN = """\
VECTOR-TRACE(1)                  User Commands                 VECTOR-TRACE(1)

NAME
    vector-trace - digitize a curve from an image of a 2D plot using Sobel
    edge detection

SYNOPSIS
    vector-trace extract IMAGE --xcal PX:VAL PX:VAL --ycal PY:VAL PY:VAL
                 [--seed X,Y | --color NAME|HEX] [--tol N]
                 [--frame X0,Y0,X1,Y1] [--thr F] [--xlog] [--ylog] [-o FILE]
    vector-trace colors IMAGE [--n N] [--frame X0,Y0,X1,Y1]
    vector-trace preview IMAGE [OPACITY] [--seed X,Y | --color NAME|HEX]
                 [--tol N] [--frame X0,Y0,X1,Y1] [--thr F]
    vector-trace --help | --man
    vector-trace extract --help | --man
    vector-trace colors --help | --man
    vector-trace preview --help | --man

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

    colors
        Identify the plot's dominant stroke colors and print each one's hex
        code, nearest common color name, and a matching color-square emoji
        (one of 🟥🟧🟨🟩🟦🟪🟫⬛⬜). Does not extract curve data.

    preview
        Trace one curve and show it, overlaid on a faded version of the
        image, in a window. OPACITY (0-100, default 40) controls how strong
        the original image is behind the overlay, to make the traced curve
        easier to see. Writes nothing to disk; close the window (any key) to
        exit. Needs a GUI-capable OpenCV build (plain "opencv-python", not
        "opencv-python-headless").

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

    With --color NAME|HEX:
        Same as --seed, but the target color is given directly as a common
        color name (e.g. "blue") or a hex code (e.g. "#1f77b4") instead of a
        pixel. The plot's actual dominant stroke colors are found internally
        (as "colors" would list them, but not printed) and the one closest to
        the requested name/hex is traced. Since there is no pixel to pick a
        specific curve, the widest stroke of that color is traced -- with
        more than one curve of the same requested color, use --seed instead.
        Mutually exclusive with --seed.

    Either way (or with neither) the result has one y value per image
    column: the middle of the traced stroke.

OPTIONS
    IMAGE               Input image.
    --xcal PX:VAL PX:VAL
                        Two x-axis reference points (required).
    --ycal PY:VAL PY:VAL
                        Two y-axis reference points (required).
    --seed X,Y          A pixel on the curve to trace, as image column, row.
                        Must be within 10 pixels of the curve. Enables color
                        tracing. Mutually exclusive with --color.
    --color NAME|HEX    A common color name ("blue") or hex code ("#1f77b4")
                        to trace, instead of a pixel seed. Matched against
                        the plot's actual dominant colors. Mutually
                        exclusive with --seed.
    --tol N             With --seed/--color: color tolerance as an RGB
                        distance (default 40). Raise it if the trace breaks
                        up along the curve; lower it if it jumps to a
                        similar-colored neighbor.
    --frame X0,Y0,X1,Y1 Plot area in pixels, replacing auto-detection. The
                        corners are the inner edges of the axis lines.
    --thr F             Without --seed/--color: edge threshold as a fraction
                        of the strongest gradient in the plot area (default
                        0.3).
    --xlog, --ylog      Logarithmic (base 10) x or y axis.
    -o, --output FILE   Output CSV path (default curve.csv).
    --help              Short usage summary.
    --man               This manual.

    colors-only:
    --n N               Number of dominant colors to report (default 5).

    preview-only:
    OPACITY             Opacity of the original image under the overlay,
                        0-100 (default 40). 0 fades it to black, 100 is full
                        strength.

OUTPUT
    FILE (CSV)
        Header "series,x,y". One row per image column the curve covers,
        sorted by x, in data units. The series name is always "curve1".

    FILE with the extension replaced by .overlay.png
        The input image with the detected plot area in green and the traced
        curve in red. Always check this image before using the numbers.

    colors prints one line per color to standard output, most common first:
    EMOJI  #HEXCODE  name  PERCENT. No file is written.

    preview opens a window with the overlay and writes no file.

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

    The same, chosen by color instead of a pixel:

        vector-trace extract fig.png --xcal 193:0 1052:12 \\
            --ycal 653.5:0 88.5:140 --color blue -o blue.csv

    Logarithmic x axis, with the plot area given explicitly:

        vector-trace extract fig.png --xcal 253.5:10 546.5:100 --xlog \\
            --ycal 471.5:10 66.5:50 --frame 168,19,837,570 -o model.csv

    Listing the dominant colors in a plot, without extracting any curve:

        vector-trace colors fig.png --n 3

    Checking a trace by eye before committing to a calibration:

        vector-trace preview fig.png --seed 908,335

    Same, with the original image faded to 15% so the curve stands out more:

        vector-trace preview fig.png 15 --seed 908,335

    Previewing a curve chosen by color instead of a pixel:

        vector-trace preview fig.png --color blue

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
    - preview needs a GUI-capable OpenCV build; it fails with a clear error
      under "opencv-python-headless" or in a headless/SSH session.

SEE ALSO
    PRD.md in the project directory for the design and roadmap.
"""
