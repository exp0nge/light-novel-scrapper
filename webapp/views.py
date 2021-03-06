# coding=utf-8
import json
import urllib2
import os

from webapp import app, celery, db
from webapp.models import Chapter
from flask import request, render_template, send_file, send_from_directory
from light_scrapper_web_api import chapters_walk_task, toc_walk_task, generate_epub, generate_zip
import traceback


@celery.task()
def ping():
    return 'OK'


def celery_status(task_id):
    return json.dumps({'taskId': task_id,
                       'state': celery.AsyncResult(task_id).state,
                       'info': (celery.AsyncResult(task_id)).info})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/ping/')
def celery_pinger():
    try:
        return json.dumps(str(celery))
    except Exception as e:
        return json.dumps({'error': str(e), 'repr': repr(e), 'trace': traceback.format_exc()})


@app.route('/init/')
def init_db():
    try:
        db.create_all()
        return json.dumps({'success': 'Init success'})
    except Exception as e:
        return json.dumps({'error': str(e), 'repr': repr(e)})


@app.route('/task/', methods=['POST'])
def novel_task():
    try:
        # scrapper.chapters_walk.delay()
        chap_task = chapters_walk_task.delay(title=request.get_json(force=True)['title'],
                                             start=request.get_json(force=True)['start'],
                                             end=request.get_json(force=True)['end'],
                                             url=request.get_json(force=True)['url'])
        return json.dumps({'taskId': str(chap_task), 'status': 'success'})
    except urllib2.URLError:
        return json.dumps({'message': 'invalid url', 'status': 'error'})


@app.route('/task/<task_id>/')
def novel_task_info(task_id):
    return celery_status(task_id)


@app.route('/task/<task_id>/chapters/')
def chapter_info(task_id):
    return json.dumps({'task': task_id, 'chapters': [{'chapter': chapter.chapter_number,
                                                      'url': chapter.url,
                                                      'content': chapter.content}
                                                     for chapter in Chapter.query.filter(Chapter.task == task_id)]})


@app.route('/task/<task_id>/chapters/task/epub/', methods=['POST'])
def epub_task(task_id):
    epub_task = generate_epub.delay(task_id, app.config['EPUB_FOLDER'])
    return json.dumps({'epubTaskId': str(epub_task), 'state': epub_task.state})


@app.route('/task/<task_id>/chapters/task/epub/<epub_task_id>/')
def epub_task_status(task_id, epub_task_id):
    return json.dumps({'epubTaskId': epub_task_id, 'state': celery.AsyncResult(epub_task_id).state})


@app.route('/task/<task_id>/chapters/d/epub/')
def epub_download(task_id):
    return send_file(os.path.join(app.config['EPUB_FOLDER'], task_id + '.epub'),
                     as_attachment=True,
                     attachment_filename=request.args.get('title') + '.epub')


@app.route('/task/<task_id>/chapters/d/zip/')
def zip_download(task_id):
    zip_file, title = generate_zip(task_id)
    return send_file(zip_file, attachment_filename=title + task_id + '.zip', as_attachment=True)


# TOC walking
@app.route('/task/toc/', methods=['POST'])
def toc_walk():
    try:
        # scrapper.chapters_walk.delay()
        toc_task = toc_walk_task.delay(title=request.get_json(force=True)['title'],
                                       start=request.get_json(force=True)['start'],
                                       end=request.get_json(force=True)['end'],
                                       url=request.get_json(force=True)['url'])
        return json.dumps({'taskId': str(toc_task), 'status': 'success'})
    except urllib2.URLError:
        return json.dumps({'message': 'invalid url', 'status': 'error'})
