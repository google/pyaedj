# py-ae-dj

## Python 3.7 API server with JavaScript responsive web app

## Goals

py-ae-dj is an experimental project helping developers use Python and Datastore
on Google App Engine. It has minimal, but all nessesary tools for setting up,
developing, testing, configuring, deploying, managining, and supporting a
typical Python App Engine application. It also shows how to develop responsive
web app in JavaScript and connect it to an REST-style API server.

## Running Locally

Execute:
* `cd ./toybox/`
* `bash manage.sh run`

Access:
* http://localhost:8080/index.html

## Deploy to App Engine Standard

Prepare:
* create new Google Cloud Platform project and related Firebase project
* modify `server_py3/main.py` and `client_js/js/main.js` to point to your own projects above

Execute:
* `cd ./toybox/`
* `bash manage.sh deploy`

Access:
* visit Google Cloud Platform to promote and access new version

