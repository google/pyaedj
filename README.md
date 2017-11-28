# py-ae-dj

Welcome!

## Goals

py-ae-dj is an experimental project helping developers use Python and Django
on Google App Engine. It has minimal, but all nessesary tools for setting up,
developing, testing, configuring, deploying, managining, and supporting a
typical Python App Engine application. It also shows how to develop Django
application with Google Cloud SQL, Google Cloud Datastore and other Google
Cloud APIs.

## Disclaimer

py-ae-dj is not an official Google product.

## Licensing

py-ae-dj is Licensed under the Apache License, Version 2.0.

## Initial Setup on Ubuntu 16.04 LTS
  * Run an update:
    * > sudo apt-get update
  * Install Python:
    * do I need to do this step? not if this works:
      * > python --version
   * run these commands:
      * > sudo apt-get install python2.7
  * Install Google Cloud SDK (gcloud, gsutils); install with:
    * do I need to do this step? not if this works:
      * > gcloud --version  # Google Cloud SDK 172.0.0
      * > gsutil --version  # gsutil version: 4.27
    * run these commands:
      * > curl https://sdk.cloud.google.com | bash
      * > exec -l $SHELL
      * > gcloud init
      * > gcloud auth application-default login
  * Install MySQL:
    * do I need to do this step? not if this works:
      * > mysql --version
    * run these commands:
      * > sudo apt-get install mysql-server
      * > sudo apt-get install libmysqlclient-dev
    * create database:
      * > mysql -u root
      * > CREATE DATABASE IF NOT EXISTS \`gaedj\` CHARACTER SET utf8 COLLATE utf8_bin;
  * Install pip:
    * do I need to do this step? not if this works:
      * > pip --version
    * run these commands:
      * > sudo apt-get install python-pip
      * > pip install --upgrade pip
  * Install global pip dependencies, which did not work in requirements.txt:
    * > sudo pip install MySQL-Python==1.2.5
  * Get this project from Github:
    * > git clone https://github.com/google/pyaedj.git
    * > cd pyaedj/platform
  * Install local pip dependencies via requirements.txt:
    * > python manage.py deps_install
  * Start local server:
    * > python manage.py app_run
  * Visit app home page:
    * > http://localhost:8080

## Before first deployment to Google App Engine
  * create a new Google Cloud Project (https://console.cloud.google.com/)
  * create an instance of cloud hosted SQL database (second generation)
    * instance id: py-ae-dj-prod
    * database version: MySQL 5.6
    * check "no password" box
    * add database flag: character_set_server=utf8
  * create new database in the above instance
    * database name: gaedj
    * character set: utf8
    * collation: utf8_bin


