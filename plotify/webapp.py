import os
import sqlite3
import json
from functools import wraps

from flask import Flask, Response, g, send_file, send_from_directory, request

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'plotify.db')
PORT = 8080

webapp = Flask(__name__)


def get_db() -> sqlite3.Connection:
    """
    Fetches a request-scoped database connection
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect("file:{}?mode=ro".format(DATABASE_PATH), uri=True)
    return db


@webapp.teardown_appcontext
def close_connection(exception):
    """
    Close database at the end of each request if required
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def json_response(f):
    @wraps(f)
    def inner(*args, **kwargs):
        result = f(*args, **kwargs)
        return Response(json.dumps(result), mimetype="application/json")
    return inner


@webapp.route("/")
def index():
    return send_file("static/index.html")


@webapp.route("/dist/<path:path>")
def static_dist(path):
    return send_from_directory("static/dist", path)


def get_data(query):
    cur = get_db().execute(query)
    result = cur.fetchall()
    return result


def parse_data(attributes, query, teachers):

    teacher_dict = dict((t['name'], t) for t in teachers)
    teacher = ''
    for each in query:
        teacher_dict[each[0]][each[1]]=each[2]

    headers = ['Teacher'] + attributes
    return_data = [headers]
     
    for teacher_object in teacher_dict.values():
        teacher_data = [teacher_object['name']]
        for attribute in attributes:
            teacher_data.append(teacher_object[attribute] if attribute in teacher_object else 0)
        return_data.append(teacher_data)

    return return_data


@webapp.route("/api/attributes")
@json_response
def get_attributes():
    """
    Should fetch a list of unique student attributes

    Response format:
    {
        attributes: [
            {
                name: "...",
            },
            ...
        ]
    }
    """
    # TODO Implement

    attributes = get_data('SELECT DISTINCT attribute FROM student_attribute')
    response = {'attributes':[{'name':item} for item in attributes]}
            
    return response


@webapp.route("/api/chart", methods=["POST"])
@json_response
def get_chart():
    """
    Should fetch the data for the chart
    The request may have POST data

    Response format:
    {
        chartType: ChartType,
        data: [Data],
        options: Options,
    }
    where ChartType, Data, and Options are as demonstrated on https://react-google-charts.com/
    """
    # TODO implement this
    
    attribute_filter = (
                        f"WHERE sa.attribute = \'{request.form['attribute']}\' "
                        if 'attribute' in request.form else ''
                       )

    query_result = get_data(
                            f'SELECT c.teacher_name, sa.attribute, COUNT(*) '
                            f'FROM class c '
                            f'JOIN student s '
                            f'ON s.class_id = c.id '
                            f'JOIN student_attribute sa '
                            f'ON sa.student_name = s.name '
                            f'{attribute_filter}'
                            f'GROUP BY c.teacher_name, sa.attribute '
                            f'ORDER BY c.teacher_name ASC'
                        )

    attributes = [obj[0] for obj in get_data(f'SELECT DISTINCT attribute FROM student_attribute as sa {attribute_filter}')]
    teachers = [{'name':obj[0]} for obj in get_data(f'SELECT DISTINCT teacher_name from CLASS ORDER BY teacher_name ASC')]
    chart_data = parse_data(attributes, query_result, teachers)

    title = f"Attribute Distribution for {request.form['attribute'] if 'attribute' in request.form else 'All Teachers'}"
    options = {
                'title':title,
                'chartArea':{
                    'top':80,
                    'left':50,
                    'width':'65%', 
                    'height':'350'
                },
                "hAxis":{
                    'textStyle':{
                        'fontSize':9
                    }
                },
                "vAxis":{
                    'gridlines':{
                        'multiple':1
                    }
                }
              }

    chart_object = {
                        'chartType':'ColumnChart',
                        'data':chart_data,
                        'options':options
                   }

    return chart_object
