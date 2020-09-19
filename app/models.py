from playhouse.flask_utils import FlaskDB
from peewee import CharField, TextField, Model
db_wrapper = FlaskDB()


class Build(db_wrapper.Model):
    id = CharField(max_length=36, primary_key=True)
    commitId = CharField(max_length=40)
    # PENDING, BUILDING, FINISHED, ERRORED
    status = CharField(max_length=16, default='PENDING')
    config = TextField()
    log = TextField(null=True)
