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
from archapp.interactive import EpicsArchive
###########################################################

#helper method created to make different markers for diffferent types of event points (completed, initiated, not comp)
def arch_plot(motor, start, end, num):
	start = str(start)+" 00:00:00"
	end = str(end)+ " 23:59:59"
	start = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
	end = datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
	pvname = 'MFX:TFS:MMS:21.RBV'
	arch = EpicsArchive()
	data = arch.get(pvname, start, end, xarray=True)
	df = data.to_dataframe()
	values = df[pvname]['vals'].tolist()
	times = data['time'].to_dataframe()['time'].tolist()
	if len(values)==1:
		values = [values[0], values[0]]
		times = [start, end]
	elif times[len(times)-1]<end:
		times.append(end)
		values.append(values[len(values)-1])
	arch_plot = go.Scatter(
        mode = 'lines',
	name = str(motor)+' Archiver Plot',
	opacity=0.3,
	showlegend = True,
        hoverinfo = 'y',
        hoverlabel = dict(bgcolor = "rgba"+plotly.colors.DEFAULT_PLOTLY_COLORS[num][3:-1]+", 0.3)"),
	line = dict(color = plotly.colors.DEFAULT_PLOTLY_COLORS[num]),
	x=times,
	y=values
	)
	legendgroup = str(motor),
	return arch_plot

def  make_scatter(startX, startY, successX, successY, stoppedX, stoppedY, motor_name):
        start = go.Scatter(
            name = 'Event Initiated',
            mode = 'markers',
            showlegend = False,
            marker = dict(
            color = 'magenta',
            size = 2,
            ),
            legendgroup = str(motor_name),
            hoverinfo = 'none',
            x=startX,
            y=startY
        )
        stop = go.Scatter(
               name = 'Event Finished',
               mode = 'markers',
               showlegend = False,
               marker = dict(
               color = 'black',
               size = 2
               ),
               hoverinfo = 'none',
               legendgroup = str(motor_name),
               x=successX,
               y=successY
           )
        stopped = go.Scatter(
               name = 'Target Not Reached',
                mode = 'markers',
                showlegend = False,
                marker = dict(
                color = 'red',
                size = 2
                ),
                hoverinfo = 'none',
                x=stoppedX,
                legendgroup = str(motor_name),
                y=stoppedY
            )
        if stoppedX!=None:
            data = [start, stop, stopped]
        else:
            data = [start, stop]
        return data

#called when an instrument is chosen from dropdown, the motor's df is found in the database for the given date range
#and appends points to lists sent to make_scatter to be given specific markers
def plot_motor(motor_name, time1, time2, num, success):
        time1=datetime.strftime(time1, "%Y-%m-%d")
        time2=datetime.strftime(time2, "%Y-%m-%d")
        wh = waitingHook(str(motor_name))
        df = wh.get_data(str(motor_name), time1, time2)
        arch = arch_plot(motor_name, time1, time2, num)
        df.columns = ['start_ts', 'finish_ts', 'start_pos', 'finish_pos', 'target', 'success', 'user']
        if df.empty:
           return [[arch],[]]
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
                    unapproved.append(unapproved_move(df, i, motor_name, num, success))

            if df['success'][i]=="False":
                stopInfo = unsuccess_line(df, stoppedX, stoppedY, i, motor_name, num, success)
                stopEvent.append(stopInfo[0])
                stoppedX = stopInfo[1]
                stoppedY = stopInfo[2]
        event = go.Scatter(
                          x=timeList,
                          y=positionList,
                          legendgroup = str(motor_name),
                          hoverinfo = 'text',
                          line = dict(color = plotly.colors.DEFAULT_PLOTLY_COLORS[num]),
                          text = ['Pos: {} <br> '.format(positionList[i]) +
                          'Time: {} <br> '.format(timeList[i])+ 'User: {} '.format(userList[i]) for i in range(len(positionList))],
                          showlegend = True,
                          name = str(motor_name)+" Movement Plot",
        )

        data = [event]+stopEvent+[arch]+unapproved+make_scatter(startX, startY, successX, successY, stoppedX, stoppedY,  motor_name)
        df.columns = ['Start Time', 'Finish Time', 'Start Position', 'Finish Position', 'Target Position', 'Success', 'User']
        return [data, df]

#if the target is not reached, the line is simulated and plotted as if it were reached as a black dashed line
def unsuccess_line(df, stoppedX, stoppedY, i, motor_name, num, success):
    finish_time = datetime.strptime(df['finish_ts'][i].replace("T", " "), '%Y-%m-%d %H:%M:%S')
    start_time = datetime.strptime(df['start_ts'][i].replace("T", " "), '%Y-%m-%d %H:%M:%S')
    stoppedX.append((df['finish_ts'][i]))
    stoppedY.append(df['target'][i])
    stopEvent = go.Scatter(
        x=((df['start_ts'][i]), (df['finish_ts'][i])),
        y=(df['start_pos'][i], df['target'][i]),
        name = 'Unsuccessful Event',
	showlegend = False,
        legendgroup = str(motor_name),
        text = str(motor_name)+" Unsuccessful Event",
        hoverinfo = 'text',
        hoverlabel = dict(bgcolor='black'),
        line = dict(
        dash = 'dash',
        color='black'
        )
    )
    if success>0:
        stopEvent.showlegend = False
    return [stopEvent, stoppedX, stoppedY]
#an unapproved move is when the previous position does not match up to start position,
#meaning the motor was moved without being told to do so
def unapproved_move(df, i, motor_name, num, success):
    unappEvent = go.Scatter(
    x=((df['finish_ts'][i-1]), (df['start_ts'][i])),
    y=(df['finish_pos'][i-1], df['start_pos'][i]),
    name = 'Unapproved Move',
    showlegend = False,
    legendgroup = str(motor_name),
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
    success=0
    for i in range(0, len(motors)):
        tabledat = []
        add_motors = plot_motor(motors[i], time1, time2,i, success)
        data += add_motors[0]
        if len(add_motors[0])>1:
            success+=1
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
                style_table={'display': 'none', 'overflow-Y':'scroll', 'maxHeight': '200px'},
                columns=[{"name": j, "id": j} for j in ['Start Time', 'Start Position', 'Finish Position', 'Target Position', 'Success', 'User']],
                fixed_rows={ 'headers': True, 'data': 0 },
                style_cell={'fontSize':15, 'font-family':'sans-serif', 'minWidth': '180px',
                 'textAlign': 'center'},
                 style_header = {'backgroundColor': plotly.colors.DEFAULT_PLOTLY_COLORS[i-1], 'color':'white'},
                id = 'table'+str(i),
                )),
    return html.Div(tbls)

#sets automatic plot to being with before user input

app = dash.Dash(__name__, url_base_pathname='/motor_flask/')
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
            {'label': 'MFX:DET:MMS:01', 'value': 'MFX:DET:MMS:01'},
            {'label': 'test', 'value': 'test'},
            {'label': 'MFX:DET:MMS:02', 'value': 'MFX:DET:MMS:02'},
            {'label': 'MFX:DET:MMS:03', 'value': 'MFX:DET:MMS:03'},
            {'label': 'MFX:DET:MMS:04', 'value': 'MFX:DET:MMS:04'},
            {'label': 'MFX:DG1:CLF:01', 'value': 'MFX:DG1:CLF:01'},
            {'label': 'MFX:DG1:CLZ:01', 'value': 'MFX:DG1:CLZ:01'},
            {'label': 'MFX:DG1:MMS:01', 'value': 'MFX:DG1:MMS:01'},
            {'label': 'MFX:DG1:MMS:09', 'value': 'MFX:DG1:MMS:09'},
            {'label': 'MFX:DG1:PIM:MOTOR', 'value': 'MFX:DG1:PIM:MOTOR'},
            {'label': 'MFX:DG1:RLM:MIRROR:MOTOR', 'value': 'MFX:DG1:RLM:MIRROR:MOTOR'},
            {'label': 'MFX:DG1:IPM:DIODE:MOTOR', 'value': 'MFX:DG1:IPM:DIODE:MOTOR'},
            {'label': 'MFX:DG1:IPM:TARGET:MOTOR', 'value': 'MFX:DG1:IPM:TARGET:MOTOR'},
            {'label': 'MFX:DG1:MMS:06', 'value': 'MFX:DG1:MMS:06'},
            {'label': 'MFX:DG1:MMS:07', 'value': 'MFX:DG1:MMS:07'},
            {'label': 'MFX:DG1:MMS:08', 'value': 'MFX:DG1:MMS:08'},
            {'label': 'MFX:DG2:IPM:DIODE:MOTOR', 'value': 'MFX:DG2:IPM:DIODE:MOTOR'},
            {'label': 'MFX:DG2:IPM:TARGET:MOTOR', 'value': 'MFX:DG2:IPM:TARGET:MOTOR'},
            {'label': 'MFX:DG2:MMS:05', 'value': 'MFX:DG2:MMS:05'},
            {'label': 'MFX:DG2:MMS:06', 'value': 'MFX:DG2:MMS:06'},
            {'label': 'MFX:DG2:MMS:07', 'value': 'MFX:DG2:MMS:07'},
            {'label': 'MFX:DG2:CLF:01', 'value': 'MFX:DG2:CLF:01'},
            {'label': 'MFX:DG2:CLZ:01', 'value': 'MFX:DG2:CLZ:01'},
            {'label': 'MFX:DG2:MMS:08', 'value': 'MFX:DG2:MMS:08'},
            {'label': 'MFX:DG2:PIM:MOTOR', 'value': 'MFX:DG2:PIM:MOTOR'},
            {'label': 'MFX:DIA:MMS:08', 'value': 'MFX:DIA:MMS:08'},
            {'label': 'MFX:DIA:MMS:09', 'value': 'MFX:DIA:MMS:09'},
            {'label': 'MFX:ROB:MMS:08', 'value': 'MFX:ROB:MMS:08'},
            {'label': 'MFX:DG1:MMS:02', 'value': 'MFX:DG1:MMS:02'},
            {'label': 'MFX:DG1:MMS:03', 'value': 'MFX:DG1:MMS:03'},
            {'label': 'MFX:DG1:MMS:04', 'value': 'MFX:DG1:MMS:04'},
            {'label': 'MFX:DG1:MMS:05', 'value': 'MFX:DG1:MMS:05'},
            {'label': 'MFX:DG2:MMS:01', 'value': 'MFX:DG2:MMS:01'},
            {'label': 'MFX:DG2:MMS:02', 'value': 'MFX:DG2:MMS:02'},
            {'label': 'MFX:DG2:MMS:03', 'value': 'MFX:DG2:MMS:03'},
            {'label': 'MFX:DG2:MMS:04', 'value': 'MFX:DG2:MMS:04'},
            {'label': 'MFX:DG2:MMS:12', 'value': 'MFX:DG2:MMS:12'},
            {'label': 'MFX:DG2:MMS:13', 'value': 'MFX:DG2:MMS:13'},
            {'label': 'MFX:DG2:MMS:14', 'value': 'MFX:DG2:MMS:14'},
            {'label': 'MFX:DG2:MMS:15', 'value': 'MFX:DG2:MMS:15'},
            {'label': 'MFX:DG2:MMS:15', 'value': 'MFX:DG2:MMS:15'},
            {'label': 'MFX:DG2:MMS:16', 'value': 'MFX:DG2:MMS:16'},
            {'label': 'MFX:DG2:MMS:17', 'value': 'MFX:DG2:MMS:17'},
            {'label': 'MFX:DG2:MMS:18', 'value': 'MFX:DG2:MMS:18'},
            {'label': 'MFX:DG2:MMS:19', 'value': 'MFX:DG2:MMS:19'},
            {'label': 'MFX:TAB:MMS:01', 'value': 'MFX:TAB:MMS:01'},
            {'label': 'MFX:TAB:MMS:02', 'value': 'MFX:TAB:MMS:02'},
            {'label': 'MFX:TAB:MMS:03', 'value': 'MFX:TAB:MMS:03'},
            {'label': 'MFX:TAB:MMS:04', 'value': 'MFX:TAB:MMS:04'},
            {'label': 'MFX:TAB:MMS:05', 'value': 'MFX:TAB:MMS:05'},
            {'label': 'MFX:TAB:MMS:06', 'value': 'MFX:TAB:MMS:06'},
            {'label': 'MFX:TFS:MMS:01', 'value': 'MFX:TFS:MMS:01'},
            {'label': 'MFX:TFS:MMS:02', 'value': 'MFX:TFS:MMS:02'},
            {'label': 'MFX:TFS:MMS:03', 'value': 'MFX:TFS:MMS:03'},
            {'label': 'MFX:TFS:MMS:04', 'value': 'MFX:TFS:MMS:04'},
            {'label': 'MFX:TFS:MMS:05', 'value': 'MFX:TFS:MMS:05'},
            {'label': 'MFX:TFS:MMS:06', 'value': 'MFX:TFS:MMS:06'},
            {'label': 'MFX:TFS:MMS:07', 'value': 'MFX:TFS:MMS:07'},
            {'label': 'MFX:TFS:MMS:08', 'value': 'MFX:TFS:MMS:08'},
            {'label': 'MFX:TFS:MMS:09', 'value': 'MFX:TFS:MMS:09'},
            {'label': 'MFX:TFS:MMS:10', 'value': 'MFX:TFS:MMS:10'},
            {'label': 'MFX:TFS:MMS:11', 'value': 'MFX:TFS:MMS:11'},
            {'label': 'MFX:TFS:MMS:12', 'value': 'MFX:TFS:MMS:12'},
            {'label': 'MFX:TFS:MMS:13', 'value': 'MFX:TFS:MMS:13'},
            {'label': 'MFX:TFS:MMS:14', 'value': 'MFX:TFS:MMS:14'},
            {'label': 'MFX:TFS:MMS:15', 'value': 'MFX:TFS:MMS:15'},
            {'label': 'MFX:TFS:MMS:16', 'value': 'MFX:TFS:MMS:16'},
            {'label': 'MFX:TFS:MMS:17', 'value': 'MFX:TFS:MMS:17'},
            {'label': 'MFX:TFS:MMS:18', 'value': 'MFX:TFS:MMS:18'},
            {'label': 'MFX:TFS:MMS:19', 'value': 'MFX:TFS:MMS:19'},
            {'label': 'MFX:TFS:MMS:20', 'value': 'MFX:TFS:MMS:20'},
            {'label': 'MFX:TFS:MMS:21', 'value': 'MFX:TFS:MMS:21'},
            {'label': 'MFX:TFS:XFLS:01:MOTOR', 'value': 'MFX:TFS:XFLS:01:MOTOR'},
            {'label': 'MFX:TFS:XFLS:02:MOTOR', 'value': 'MFX:TFS:XFLS:02:MOTOR'},
            {'label': 'MFX:TFS:XFLS:03:MOTOR', 'value': 'MFX:TFS:XFLS:03:MOTOR'},
            {'label': 'MFX:TFS:XFLS:04:MOTOR', 'value': 'MFX:TFS:XFLS:04:MOTOR'},
            {'label': 'MFX:TFS:XFLS:05:MOTOR', 'value': 'MFX:TFS:XFLS:05:MOTOR'},
            {'label': 'MFX:TFS:XFLS:06:MOTOR', 'value': 'MFX:TFS:XFLS:06:MOTOR'},
            {'label': 'MFX:TFS:XFLS:07:MOTOR', 'value': 'MFX:TFS:XFLS:07:MOTOR'},
            {'label': 'MFX:TFS:XFLS:08:MOTOR', 'value': 'MFX:TFS:XFLS:08:MOTOR'},
            {'label': 'MFX:TFS:XFLS:09:MOTOR', 'value': 'MFX:TFS:XFLS:09:MOTOR'},
            {'label': 'MFX:TFS:XFLS:10:MOTOR', 'value': 'MFX:TFS:XFLS:10:MOTOR'},
            {'label': 'MFX:USR:MMS:17', 'value': 'MFX:USR:MMS:17'},
            {'label': 'MFX:USR:MMS:18', 'value': 'MFX:USR:MMS:18'},
            {'label': 'MFX:USR:MMS:19', 'value': 'MFX:USR:MMS:19'},
            {'label': 'MFX:USR:MMS:20', 'value': 'MFX:USR:MMS:20'},
            {'label': 'MFX:USR:MMS:21', 'value': 'MFX:USR:MMS:21'},
            {'label': 'MFX:USR:MMS:22', 'value': 'MFX:USR:MMS:22'},
            {'label': 'MFX:USR:MMS:23', 'value': 'MFX:USR:MMS:23'},
            {'label': 'MFX:USR:MMS:24', 'value': 'MFX:USR:MMS:24'},
            {'label': 'MFX:USR:MMS:01', 'value': 'MFX:USR:MMS:01'},
            {'label': 'MFX:USR:MMS:02', 'value': 'MFX:USR:MMS:02'},
            {'label': 'MFX:USR:MMS:03', 'value': 'MFX:USR:MMS:03'},
            {'label': 'MFX:USR:MMS:04', 'value': 'MFX:USR:MMS:04'},
            {'label': 'MFX:USR:MMS:05', 'value': 'MFX:USR:MMS:05'},
            {'label': 'MFX:USR:MMS:06', 'value': 'MFX:USR:MMS:06'},
            {'label': 'MFX:USR:MMS:07', 'value': 'MFX:USR:MMS:07'},
            {'label': 'MFX:USR:MMS:08', 'value': 'MFX:USR:MMS:08'},
            {'label': 'MFX:USR:MMS:09', 'value': 'MFX:USR:MMS:09'},
            {'label': 'MFX:USR:MMS:10', 'value': 'MFX:USR:MMS:10'},
            {'label': 'MFX:USR:MMS:11', 'value': 'MFX:USR:MMS:11'},
            {'label': 'MFX:USR:MMS:12', 'value': 'MFX:USR:MMS:12'},
            {'label': 'MFX:USR:MMS:13', 'value': 'MFX:USR:MMS:13'},
            {'label': 'MFX:USR:MMS:14', 'value': 'MFX:USR:MMS:14'},
            {'label': 'MFX:USR:MMS:15', 'value': 'MFX:USR:MMS:15'},
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
            style = {'backgroundColor':'white','display':'none', 'width' : 1300}),
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
    if len(graphs[0].data) == 1:
        outputs = [graphs[0], {'display': '', 'backgroundColor':'white'}, ('Only Archiver plot for selected dates and motor(s), no motor movements')]
        for i in range(1, 6):
            outputs.append([]),
            outputs.append({'display': 'none'}),
            outputs.append({})
        return outputs
    if graphs[0].data==():
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
    outputs = [graphs[0], {'display': '','backgroundColor':'white', 'padding':20}, ('')]
    for i in range(1, 6):
        if isinstance(graphs[i], pd.DataFrame):
            graphs[i] = graphs[i].loc[:, graphs[i].columns !='Finish Time']
            outputs.append(graphs[i].to_dict('records')),
            outputs.append({'overflow-Y':'scroll', 'maxHeight': '200px', 'display':'', 'minWidth':'1300', 'padding':60, 'padding-top':20, 'padding-bottom':10})
            outputs.append({'backgroundColor': plotly.colors.DEFAULT_PLOTLY_COLORS[i-1],'color':'white'})
        else:
            outputs.append([]),
            outputs.append({'display': 'none', 'overflow-Y':'scroll', 'maxHeight': '10'})
            outputs.append({'backgroundColor': plotly.colors.DEFAULT_PLOTLY_COLORS[i-1],'color':'white'})
    return outputs




if __name__ == '__main__':
    app.run_server(debug=False)
