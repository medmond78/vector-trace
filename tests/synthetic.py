"""Synthetic plots with exact ground truth for testing."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

W, H, DPI = 800, 600, 100


def make_plot(path, kind="linear"):
    """kind: linear | logx | dashed. Returns xcal, ycal (pixel indices), truth(x)->y and x_range."""
    fig, ax = plt.subplots(figsize=(W / DPI, H / DPI), dpi=DPI)
    if kind == "logx":
        x_range = (1.0, 1000.0)
        truth = lambda x: 2 + np.sin(2 * np.log10(x))
        ax.set_xscale("log")
        ax.set_ylim(0, 4)
        xv = (10.0, 100.0)
        yv = (1.0, 3.0)
    else:
        x_range = (0.0, 10.0)
        truth = lambda x: 3 + 2 * np.sin(0.6 * x)
        ax.set_ylim(0, 6)
        xv = (2.0, 8.0)
        yv = (1.0, 5.0)
    ax.set_xlim(*x_range)
    x = np.geomspace(*x_range, 800) if kind == "logx" else np.linspace(*x_range, 800)
    ax.plot(x, truth(x), color="black", linewidth=1.5, linestyle="--" if kind == "dashed" else "-")
    ax.grid(True, color="0.85", linewidth=0.5)
    fig.savefig(path)
    plt.close(fig)

    def px(val):  # data -> pixel index (matplotlib continuous coords: index = coord - 0.5)
        d = ax.transData.transform((val, 0))
        return d[0] - 0.5

    def py(val):
        d = ax.transData.transform((x_range[0], val))
        return H - d[1] - 0.5

    return dict(
        xcal=[(px(v), v) for v in xv],
        ycal=[(py(v), v) for v in yv],
        truth=truth,
        x_range=x_range,
    )
