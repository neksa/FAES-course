from flask import Flask, render_template
from flask import make_response, request, abort

from analysis import get_logo

app = Flask(__name__)


@app.route('/')
def index():
    name = request.args.get('name')
    return render_template('index.html', name=name)


@app.route('/logo/<name>.png')
def logo(name):
    if len(name) == 0:
        abort(404)

    logo_data = None
    try:
        logo_data = get_logo(name)
    except:
        abort(500)

    if logo_data is None:
        abort(404)

    response = make_response(logo_data)
    response.headers['Content-Type'] = 'image/png'
    # response.headers['Content-Disposition'] = 'attachment; filename=logo.png'
    return response


if __name__ == '__main__':
    app.run(debug=True)
