from SQLgenie import db,app
from SQLgenie.models import User
app.app_context().push()
db.create_all()


if __name__=='__main__':
    app.run(debug=True)    