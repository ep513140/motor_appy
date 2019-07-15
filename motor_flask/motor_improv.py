import dash
import dash_core_components as dcc
import dash_html_components as html
from datetime import datetime
import pandas as pd
import plotly
import plotly.graph_objs as go
import simplejson as json
import ipywidgets as widgets
from datetime import timedelta
import dateutil.parser
from make_mysql import waitingHook
import dash_table
import time
from textwrap import dedent

###########################################################

#helper method created to make different markers for diffferent types of event points (completed, initiated, not comp)
def make_scatter(startX, startY, successX, successY, stoppedX, stoppedY, num, motor_name):
        start = go.Scatter(
            name = 'Event Initiated',
            mode = 'markers',
            marker = dict(
            color = 'magenta',
            size = 2,
            ),
            hoverinfo = 'none',
            x=startX,
            y=startY
        )
        stop = go.Scatter(
               name = 'Event Finished',
               mode = 'markers',
               marker = dict(
               color = 'black',
               size = 2
               ),
               hoverinfo = 'none',
               x=successX,
               y=successY
           )
        stopped = go.Scatter(
               name = 'Target Not Reached',
                mode = 'markers',
                marker = dict(
                color = 'red',
                size = 2
                ),
                hoverinfo = 'none',
                x=stoppedX,
                y=stoppedY
            )
        #only shows the legend for stopped and finished points if first time, prevents duplicate legend info
        if num>0:
            start.showlegend = False
            stopped.showlegend = False
            stop.showlegend = False
        if stoppedX!=None:
            data = [start, stop, stopped]
        else:
            data = [start, stop]
        return data

#called when an instrument is chosen from dropdown, the motor's df is found in the database for the given date range
#and appends points to lists sent to make_scatter to be given specific markers
def plot_motor(motor_name, time1, time2, num):
        time1=datetime.strftime(time1, "%Y-%m-%d")
        time2=datetime.strftime(time2, "%Y-%m-%d")
        wh = waitingHook(str(motor_name))
        df = wh.get_data(str(motor_name), time1, time2)
        df.columns = ['start_ts', 'finish_ts', 'start_pos', 'finish_pos', 'target', 'success', 'user']
        if df.empty:
            return ([],[])
        timeList = []
        positionList = []
        stoppedX = []
        stoppedY=[]
        startX = []
        startY = []
        successX = []
        successY = []
        stopEvent = []
        userList = []
        unapproved = []
        for i in range(0, df.shape[0]):
            timeList.append((df['start_ts'][i]))
            timeList.append((df['finish_ts'][i]))
            positionList.append(df['start_pos'][i])
            positionList.append(df['finish_pos'][i])
            userList.append(df['user'][i])
            userList.append(df['user'][i])
            startX.append((df['start_ts'][i]))
            startY.append((df['start_pos'][i]))
            successX.append((df['finish_ts'][i]))
            successY.append(df['finish_pos'][i])
            if i>0:
                if df['start_pos'][i]!=df['finish_pos'][i-1]:
                    unapproved.append(unapproved_move(df, i, motor_name))

            if df['success'][i]=="False":
                stopInfo = unsuccess_line(df, stoppedX, stoppedY, i, motor_name)
                stopEvent.append(stopInfo[0])
                stoppedX = stopInfo[1]
                stoppedY = stopInfo[2]
        event = go.Scatter(
                          x=timeList,
                          y=positionList,
                          hoverinfo = 'text',
                          line = dict(color = plotly.colors.DEFAULT_PLOTLY_COLORS[num]),
                          text = ['Pos: {} <br> '.format(positionList[i]) +
                          'Time: {} <br> '.format(timeList[i])+ 'User: {} '.format(userList[i]) for i in range(len(positionList))],
                          showlegend = True,
                          name = str(motor_name)+" Activity",
        )
        data = [event]+stopEvent+unapproved+make_scatter(startX, startY, successX, successY, stoppedX, stoppedY, num, motor_name)
        return [data, df]

#if the target is not reached, the line is simulated and plotted as if it were reached as a black dashed line
def unsuccess_line(df, stoppedX, stoppedY, i, motor_name):
    finish_time = datetime.strptime(df['finish_ts'][i].replace("T", " "), '%Y-%m-%d %H:%M:%S')
    start_time = datetime.strptime(df['start_ts'][i].replace("T", " "), '%Y-%m-%d %H:%M:%S')
    #diff = float((finish_time-start_time).seconds)
    #m = (df['finish_pos'][i]-df['start_pos'][i])/(diff)
    #hypoTime = abs(round((df['target'][i]/m-df['finish_pos'][i]/m)))
    #targetTime = timedelta(seconds = hypoTime)+finish_time
    stoppedX.append((df['finish_ts'][i]))
    stoppedY.append(df['target'][i])
    stopEvent = go.Scatter(
        x=((df['start_ts'][i]), (df['finish_ts'][i])),
        y=(df['start_pos'][i], df['target'][i]),
        showlegend = False,
        text = str(motor_name)+" Unsuccessful Event",
        hoverinfo = 'text',
        line = dict(
        dash = 'dash',
        color='black'
        )
    )
    return [stopEvent, stoppedX, stoppedY]
#creates the normal ranges for each motor to help troubleshoot if the motor stopped working accidentally
def bar_range(motorColor, df):
    startTime= df['start_ts'][0]
    endTime = df['finish_ts'][df.shape[0]-1]
    trace = go.Bar(
        name = "2018", orientation = "h",
        y = [101],
        x = [endTime],
        #opacity = 0.6,
        hoverinfo = 'skip',
        width = 2,
        showlegend = False,
    )
    trace1 = go.Bar(
        name = "2018", orientation = "h",
        y = [124],
        x = [endTime],
        #opacity = 0.6,
        hoverinfo = 'skip',
        width = 2,
        showlegend = False,
    )
    return([trace, trace1])

#an unapproved move is when the previous position does not match up to start position,
#meaning the motor was moved without being told to do so
def unapproved_move(df, i, motor_name):
    unappEvent = go.Scatter(
    x=((df['finish_ts'][i-1]), (df['start_ts'][i])),
    y=(df['finish_pos'][i-1], df['start_pos'][i]),
    showlegend = False,
    text = str(motor_name)+" Unapproved Move",
    hoverinfo = 'text',
    line = dict(
    dash = 'dash',
    color='white'
    )
    )
    return unappEvent


#called when motors are added or date is changed, uploads data into a plot and makes a table with the complete data
def add_motors(motors, time1, time2):
    data=[]
    tables = []
    finalList = [0]
    for i in range(0, len(motors)):
        tabledat = []
        add_motors = plot_motor(motors[i], time1, time2, i)
        data += add_motors[0]
        if data==([]):
            finalList.append('[]')
            continue;
        finalList.append(add_motors[1])
    for i in range(len(motors), 6):
        finalList.append('[]')
    f = go.Figure(data=data)
    finalList[0] = f
    return finalList

def add_tbls(graphs):
    tbls = []
    for i in range(1, 6):
        tbls.append(dash_table.DataTable(
                data = [],
                style_table={'display': 'none', 'overflow-Y':'scroll', 'maxHeight': '150'},
                columns=[{"name": j, "id": j} for j in ['start_ts', 'finish_ts', 'start_pos', 'finish_pos', 'target', 'success', 'user']],
                fixed_rows={ 'headers': True, 'data': 0 },
                style_cell={'fontSize':15, 'font-family':'sans-serif', 'minWidth': '180px',
                 'textAlign': 'center'},
                 style_header = {'backgroundColor': plotly.colors.DEFAULT_PLOTLY_COLORS[i-1], 'color':'white'},
                id = 'table'+str(i),
                )),
    return html.Div(tbls)

#sets automatic plot to being with before user input

app = dash.Dash(__name__)
server = app.server
app.layout = html.Div([

    dcc.DatePickerRange(
    id='my-date-picker-range',
    min_date_allowed=datetime(1995, 8, 5),
    max_date_allowed=datetime(3000, 9, 19),
    start_date=datetime.today().strftime('%Y-%m-%d'),
    end_date=datetime.today().strftime('%Y-%m-%d'),
    style={'padding':20}
),
    dcc.Dropdown(
        id='my-dropdown',
        options=[
            {'label': 'MFX', 'value': 'MFX'},
            {'label': 'test', 'value': 'test'},
            {'label': 'AMO', 'value': 'AMO'},
            {'label': 'CXI', 'value': 'CXI'},
            {'label': 'MEC', 'value': 'MEC'},
            {'label': 'SXR', 'value': 'SXR'},
            {'label': 'XCS', 'value': 'XCS'},
            {'label': 'XPP', 'value': 'XPP'},
            {'label': 'testTable', 'value': 'testTable'}
        ],
        style={'padding-left':20, 'padding-right': 20, 'padding-bottom':5, 'padding-top':5, 'fontSize':18},
        value = [],
        placeholder = "Select motor(s)",
        multi=True
    ),
    dcc.Markdown(
    dedent(
        '''

        No activity for selected dates and motor(s)
        '''
    ),
    id = 'text',
    style = {'padding':20}
    ),
    dcc.Graph(
            figure = {'data' : [go.Bar(
            x=['giraffes'],
            y=[2] )]},
            id = 'plot_motor',
            style = {'display':'none', 'width' : 1300}),
    add_tbls([]),
    html.Div(id='output-container')
])



@app.callback(
    [dash.dependencies.Output(component_id='plot_motor', component_property='figure'),
    dash.dependencies.Output(component_id='plot_motor', component_property = 'style'),
    dash.dependencies.Output(component_id='text', component_property='children'),
    dash.dependencies.Output(component_id='table1', component_property='data'),
    dash.dependencies.Output(component_id='table1', component_property='style_table'),
    dash.dependencies.Output(component_id='table1', component_property='style_header'),
    dash.dependencies.Output(component_id='table2', component_property='data'),
    dash.dependencies.Output(component_id='table2', component_property='style_table'),
    dash.dependencies.Output(component_id='table2', component_property='style_header'),
    dash.dependencies.Output(component_id='table3', component_property='data'),
    dash.dependencies.Output(component_id='table3', component_property='style_table'),
    dash.dependencies.Output(component_id='table3', component_property='style_header'),
    dash.dependencies.Output(component_id='table4', component_property='data'),
    dash.dependencies.Output(component_id='table4', component_property='style_table'),
    dash.dependencies.Output(component_id='table4', component_property='style_header'),
    dash.dependencies.Output(component_id='table5', component_property='data'),
    dash.dependencies.Output(component_id='table5', component_property='style_table'),
    dash.dependencies.Output(component_id='table5', component_property='style_header'),],
    [dash.dependencies.Input(component_id='my-date-picker-range', component_property='start_date'),
    dash.dependencies.Input(component_id='my-date-picker-range', component_property='end_date'),
    dash.dependencies.Input(component_id='my-dropdown', component_property='value'),
    ])

def update_chart(start_date, end_date, motors):
    graphs = add_motors(motors, datetime.strptime(start_date, '%Y-%m-%d'), datetime.strptime(end_date, '%Y-%m-%d'))
    if graphs == () or graphs==[{'data': []}, '[]', '[]', '[]', '[]', '[]', '[]']:
        outputs = [{'data':[]}, {'display': 'none'}, ('No activity for selected dates and motor(s)')]
        for i in range(1, 6):
            outputs.append([]),
            outputs.append({'display': 'none'}),
            outputs.append({})
        return outputs
    if len(start_date)>15:
        start_date = start_date[:-9]
    if len(end_date)>15:
        end_date = end_date[:-9]
    outputs = [graphs[0], {'display': '', 'padding':20}, ('')]
    for i in range(1, 6):
        if isinstance(graphs[i], pd.DataFrame):
            outputs.append(graphs[i].to_dict('records')),
            outputs.append({'overflow-Y':'scroll', 'maxHeight': '150', 'display':'', 'minWidth':1300, 'padding':20})
            outputs.append({'backgroundColor': plotly.colors.DEFAULT_PLOTLY_COLORS[i-1],'color':'white'})
        else:
            outputs.append([]),
            outputs.append({'display': 'none', 'overflow-Y':'scroll', 'maxHeight': '150'})
            outputs.append({'backgroundColor': plotly.colors.DEFAULT_PLOTLY_COLORS[i-1],'color':'white'})
    return outputs




if __name__ == '__main__':
    app.run_server(debug=True)
