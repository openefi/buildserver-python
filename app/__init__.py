from flask import Flask, jsonify, request, send_file
import config
import subprocess
import uuid
import json
import pathlib
import os
import tempfile
from shutil import copyfile
from hashlib import sha256
import requests
from datetime import datetime

from flask_pydantic_spec import FlaskPydanticSpec, Response

from .models import db_wrapper, Build
from .celery import make_celery

BUILD_NAMESPACE = uuid.UUID('dc3606bb-8007-454f-8974-09cd2a517f14')
app = Flask(__name__)
app.config.from_object(config)
db_wrapper.init_app(app)
celery = make_celery(app)

api = FlaskPydanticSpec('flask')
api.register(app)


@app.route('/', methods=['GET'])
@api.validate(resp=Response('HTTP_203'), tags=['test', 'demo'])
def with_code_header():
    """
    Esto no le des pelota que soy yo boludeando con pydantic
    """
    return jsonify(language=request.context.headers.Lang), 203, {'X': 233}


@app.route('/build', methods=['POST'])
def create_build():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    build_config = json.dumps(request.json.get('config', []))

    # Creamos un ID de build basado en la configuración y en el commit target
    # Para eso necesitamos el ID del ultimo commit de openefi
    data = requests.get("https://api.github.com/repos/openefi/openefi/commits/master").json()
    commit_id = data['sha']
    date_obj = datetime.now().time()
    time_str = date_obj.strftime("%H:%M:%S.%f")

    build_payload = sha256((build_config + commit_id + time_str).encode())
    build_id = uuid.uuid5(BUILD_NAMESPACE, build_payload.hexdigest())

    try:
        bld = Build.get(Build.id == build_id)
    except Build.DoesNotExist:
        bld = Build.create(id=build_id, commitId=commit_id, config=config)

    if bld.status in ('PENDING', 'ERRORED'):
        build.delay(build_id)

    return {
        'id': build_id,
        'commitId': commit_id,
        'status': 'PENDING'
    }


@app.route('/build/<build_id>', methods=['GET'])
def get_build(build_id):
    try:
        build_obj = Build.get(Build.id == build_id)
    except Build.DoesNotExist:
        return {
            'error': 'Build does not exist'
        }, 404

    return {
        'id': build_obj.id,
        'commitId': build_obj.commitId,
        'status': build_obj.status,
        # 'log': build.log
    }


@app.route('/build/<build_id>/bin', methods=['GET'])
def get_bin(build_id):
    try:
        build_obj = Build.get(Build.id == build_id)
    except Build.DoesNotExist:
        return {
            'error': 'Build does not exist'
        }, 404
    if build_obj.status != 'FINISHED':
        return {'error': 'Build not finished'}, 400

    buildpath = str(pathlib.Path(
        __file__).parent.parent.absolute().joinpath('builds'))
    if not os.path.isfile(f"{buildpath}/{build_obj.id}.bin"):
        return {'error': 'Build output not found'}, 400

    return send_file(f"{buildpath}/{build_obj.id}.bin", "application/octet-stream")


@celery.task(soft_time_limit=30, time_limit=45)
def build(build_id):
    buildpath = str(pathlib.Path(
        __file__).parent.parent.absolute().joinpath('builds'))
    try:
        bld = Build.get(Build.id == build_id)
    except Build.DoesNotExist:
        return False
    bld.status = 'IN_PROGRESS'
    bld.save()
    # Creamos un directorio temporal
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.chdir(tmpdirname)
        log = b""
        # clonamos el repo
        try:
            log += subprocess.check_output(['git', 'init'])
            log += subprocess.check_output(['git', 'remote', 'add', 'origin', 'https://github.com/openefi/openefi'])
            log += subprocess.check_output(['git', 'fetch', 'origin', bld.commitId, '--depth=1'])
            log += subprocess.check_output(['git', 'reset', '--hard', 'FETCH_HEAD'])
            log += subprocess.check_output(['git', 'submodule', 'update', '--init', '--recursive'])
            log += subprocess.check_output(['touch', 'RELEASE_CI'])
            # build
            log += subprocess.check_output(['pio', 'run'])
            # Copiamos el output
            # TODO: Auto detectar targets?
            copyfile(".pio/build/black_f407vg/firmware.bin",
                     f"{buildpath}/{bld.id}.bin")
            copyfile(".pio/build/black_f407vg/firmware.elf",
                     f"{buildpath}/{bld.id}.elf")
            bld.status = 'FINISHED'
        except Exception as e:
            print(e)
            bld.status = 'ERRORED'

        bld.log = log.decode()
        bld.save()
    return bld.status
