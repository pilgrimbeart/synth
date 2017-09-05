"""Plot charts using online Plotly service.
To configure, follow the instructions here:
https://plot.ly/python/getting-started/
"""

import plotly.plotly as py
import plotly.graph_objs as go
import random
import datetime

def plot_histo(x_range, y_values, ref_values):
    """Create a trace online, and return URL to it."""
    num_values = len(y_values)
    max_y = max(y_values)
    x_values = []
    for i in range(num_values):
        frac = i/float(num_values)
        x_values.append(frac * x_range)

    trace1 = go.Scatter(
        x=x_values,
        y=ref_values,
        name="Expected"
    )
    trace2 = go.Bar(
        x=x_values,
        y=y_values,
        name="Actual"
    )
    data = [trace1, trace2]

    layout = go.Layout(
        title='DevicePilot responses seen as of {:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()),

        xaxis=dict(
            title='modulo time (s)',
            titlefont=dict(
                family='Courier New, monospace',
                size=18,
                color='#7f7f7f'
            )
        ),
        yaxis=dict(
            title='number of events',
            titlefont=dict(
                family='Courier New, monospace',
                size=18,
                color='#7f7f7f'
            )
        )
    )
    fig = go.Figure(data=data, layout=layout)

    url = py.plot(fig, auto_open=False, fileopt="new")

    return url + ".embed" # just the plot

if __name__ == "__main__":
    XRANGE = 100
    BINS = 10
    y_values = [random.random()*10 for x in range(BINS)]
    ref_values = [random.random()*10 for x in range(BINS)]
    print "URL is", plot_histo(XRANGE, y_values, ref_values)
