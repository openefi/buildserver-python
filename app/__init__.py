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

from .models import db_wrapper, Build
from .celery import make_celery

BUILD_NAMESPACE = uuid.UUID('dc3606bb-8007-454f-8974-09cd2a517f14')
app = Flask(__name__)
app.config.from_object(config)
db_wrapper.init_app(app)
celery = make_celery(app)


@app.route('/build', methods=['POST'])
def create_build():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request"), 400

    config = json.dumps(request.json.get('config', []))

    # Creamos un ID de build basado en la configuración y en el commit target
    # Para eso necesitamos el ID del ultimo commit de openefi
    data = requests.get("https://api.github.com/repos/openefi/openefi/commits/master").json()
    commitId = data['sha']

    buildIdPayload = sha256((config + commitId).encode())
    buildId = uuid.uuid5(BUILD_NAMESPACE, buildIdPayload.hexdigest())

    try:
        bld = Build.get(Build.id == buildId)
    except Build.DoesNotExist:
        bld = Build.create(id=buildId, commitId=commitId, config=config)

    if bld.status in ('PENDING', 'ERRORED'):
        build.delay(buildId)

    return {
        'id': buildId,
        'commitId': commitId,
        'status': 'PENDING'
    }


@app.route('/build/<buildId>', methods=['GET'])
def get_build(buildId):
    try:
        build = Build.get(Build.id == buildId)
    except Build.DoesNotExist:
        return {
                   'error': 'Build does not exist'
               }, 404

    return {
        'id': build.id,
        'commitId': build.commitId,
        'status': build.status,
        # 'log': build.log
    }


@app.route('/build/<buildId>/bin', methods=['GET'])
def get_bin(buildId):
    try:
        build = Build.get(Build.id == buildId)
    except Build.DoesNotExist:
        return {
                   'error': 'Build does not exist'
               }, 404
    if build.status != 'FINISHED':
        return {'error': 'Build not finished'}, 400

    buildpath = str(pathlib.Path(__file__).parent.parent.absolute().joinpath('builds'))
    if not os.path.isfile(f"{buildpath}/{build.id}.bin"):
        return {'error': 'Build output not found'}, 400

    return send_file(f"{buildpath}/{build.id}.bin", "application/octet-stream")


@celery.task
def build(buildId):
    buildpath = str(pathlib.Path(__file__).parent.parent.absolute().joinpath('builds'))
    try:
        bld = Build.get(Build.id == buildId)
    except Build.DoesNotExist:
        return False
    bld.status = 'IN_PROGRESS'
    bld.save()

    # Creamos un directorio temporal
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.chdir(tmpdirname)
        log = ""
        # clonamos el repo
        try:
            log += subprocess.check_output(['git', 'init']).decode()
            log += subprocess.check_output(['git', 'remote', 'add', 'origin', 'https://github.com/openefi/openefi']).decode()
            log += subprocess.check_output(['git', 'fetch', 'origin', bld.commitId, '--depth=1']).decode()
            log += subprocess.check_output(['git', 'reset', '--hard', 'FETCH_HEAD']).decode()
            # build
            log += subprocess.check_output(['pio', 'run']).decode()

            # Copiamos el output
            # TODO: Auto detectar targets?
            copyfile("./.pio/build/bluepill_f103c8/firmware.bin", f"{buildpath}/{bld.id}.bin")
            copyfile("./.pio/build/bluepill_f103c8/firmware.elf", f"{buildpath}/{bld.id}.elf")
            bld.status = 'FINISHED'
        except Exception as e:
            print(e)
            bld.status = 'ERRORED'

        bld.log = log
        bld.save()
    return bld.status
