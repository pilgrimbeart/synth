"""Plot charts using online Plotly service.
To configure, follow the instructions here:
https://plot.ly/python/getting-started/
"""

import plotly.plotly as py
import plotly.graph_objs as go
import plotly
import random, logging, datetime
import os, errno

DIRECTORY = "../synth_logs/plots/"

def plot_histo(x_range, ref_values,
               histo_list):
    """Create a plot and return as a DIV string"""
    num_values = len(histo_list[0])
    x_values = []

    max_y = 0
    for H in histo_list:
        max_y = max(max_y, max(H))
    if max_y > 1:
        ref_values = [v * max_y for v in ref_values]    # Scale ref_values to height of y axis

    for i in range(num_values):
        frac = i/float(num_values)
        x_values.append(frac * x_range)

    
    trace1 = go.Scatter(x=x_values, y=ref_values, name="Expected events", marker=dict(color='rgb(0,0,0)'))
    trace2 = go.Bar(x=x_values, y=histo_list[0], name="Actual events (OK)", marker=dict(color='rgb(0,192,0)'))
    trace3 = go.Bar(x=x_values, y=histo_list[1], name="Actual events (Duplicate)", marker=dict(color='rgb(255,0,0)'))
    trace4 = go.Bar(x=x_values, y=histo_list[2], name="Actual events (Outside window)", marker=dict(color='rgb(0,0,255)'))
    trace5 = go.Bar(x=x_values, y=histo_list[3], name="Missed events", marker=dict(color='rgb(128,128,128)'))
    data = [trace1, trace2, trace3, trace4, trace5]

    layout = go.Layout(
        title='',
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

    # url = py.plot(fig, auto_open=False, filename="synth") + ".embed" # Or fileopt="new" for a new plot
    return plotly.offline.plot(fig, output_type = 'div', auto_open=False)


def plot_score_log(score_log):
    x_values = [ '{:%Y-%m-%d %H:%M:%S} GMT'.format(datetime.datetime.fromtimestamp(v[0])) for v in score_log]
    y_values = [v[1] for v in score_log]
    trace = go.Scatter(x=x_values, y=y_values, name="Score", marker=dict(color='rgb(0,0,0)'))
    data = [trace]

    layout = go.Layout(
        title='',
        xaxis=dict(
            title='time',
            titlefont=dict(
                family='Courier New, monospace',
                size=18,
                color='#7f7f7f'
            ),
            tickangle=90
            # tickformat='%a %H:%M' # Doesn't work?
        ),
        yaxis=dict(
            title='score',
            titlefont=dict(
                family='Courier New, monospace',
                size=18,
                color='#7f7f7f'
            )
        )
    )
    fig = go.Figure(data=data, layout=layout)

    return plotly.offline.plot(fig, output_type = 'div', auto_open=False)

def mkdir_p(path):
    try:
        os.makedirs(path)
        logging.info("Created log directory "+path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def write_page(instance_name, divs):
    mkdir_p(DIRECTORY)
    filename = DIRECTORY+instance_name+'.html'
    logging.info("Writing plot "+filename)
    f = open(filename,"wt")
    f.write("<HTML>\n<HEAD></HEAD>\n<BODY>\n")
    for div in divs:
        f.write('<DIV style="height: 50%;">\n') # Plotly produces its own divs, which occupy 100%, so wrap in another so we can control height
        f.write(div)
        f.write('\n</DIV>\n')
    f.write("\n</BODY>\n</HTML>\n")
    f.close()
    logging.info("Finished writing plot")
    # title='Score ' + '%.3f' % (score*100) + '% at {:%Y-%m-%d %H:%M:%S} GMT'.format(datetime.datetime.now()),


if __name__ == "__main__":
    XRANGE = 100
    BINS = 10
    y_values = [random.random()*10 for x in range(BINS)]
    ref_values = [random.random()*10 for x in range(BINS)]
    print("URL is", plot_histo(1.0, XRANGE, ref_values, y_values, y_values, y_values, y_values))
