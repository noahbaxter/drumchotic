"""Fit once, then print the report and render the plots from that one fit.

python -m drumchotic [plot names ...]
"""
import sys

from . import pipeline
from .tools import plots, report

if __name__ == '__main__':
    r = pipeline.run()
    report.show(r)
    print()
    plots.render(r, sys.argv[1:])
