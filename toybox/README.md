# py-ae-dj

## Python 3.7 API server with JavaScript responsive web app

## Goals

py-ae-dj is an experimental project helping developers use Python and Datastore
on Google App Engine. It has minimal, but all necessary tools for setting up,
developing, testing, configuring, deploying, managining, and supporting a
typical Python App Engine application. It also shows how to develop responsive
web app in JavaScript and connect it to an REST-style API server.

## How to Run

* setup new Google Coud account and project
* setup new Fiebase project
  * create new Firebase App
  * enable Real Time Database
  * enable Google Auth
* in Google Cloud Console enable Datastore in Native mode
    * launch Google Cloud Shell
    * git clone this repo
    * `cd ./toybox/`
* put your project name into
  * `./manage.sh`
  * `./server_py3/main.py`
* put your Firebase app info into
  * `./client_js/js/main.js`
* start server locally
  * `bash manage.sh run`
  * access at http://localhost:8080/index.html
* deploy to App Engine Standard
  * enable billing on your account
  * `bash manage.sh deploy`
  * visit Google Cloud Platform to promote and access new version

## Functionality

This is a core multiuser app that lets members to configure their profiles, to make posts, and to up/down votes of other members.

Few selected features:
* on the font-end
  * responsive HTML with pure JQuery and Bootstrap, Closure compiled
  * Google account login
  * navs
  * public/private views; navigation between views
  * deep view linking
  * paginated list views & forms
  * HTML form lyfecycle; POST followed by GET; error mapping to form fields
  * REST data marshaling
  * disabling UX while RPC in progress, progress indicator, error handling
  * user presence (via Firebase)
  * observability
  * testability
* on the back end
  * REST service backend with Google account auth
  * Firebase to App Engine user identity mapping
  * user roles & permissions model
  * common patterns for working with Datastore
  * server side access to Google Cloud APIs
  * static hosting, HTTP cache control
  * observability
  * testability
* glue
  * scripts to run locally and push to production


## Screnshots (Desktop)

<p>
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/w-00-login.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/w-01-register.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/w-01-register@validation.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/w-02-home.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/w-04-profile@edit.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/w-04-profile@updated.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/w-04-profile@validation.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/w-06-members.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/w-07-posts.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/w-08-post@edit.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/w-09-posts.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/w-10-voteup.png">
</p>


## Screnshots (Mobile)

<p>
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/00-login.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/01-register.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/01-register@validation.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/02-home.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/03-nav.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/04-profile.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/04-profile@edit.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/04-profile@updated.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/05-loading.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/06-members.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/07-posts.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/08-post.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/08-post@edit.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/09-posts.png">
  <img width="200px" src="https://raw.githubusercontent.com/google/pyaedj/master/docs/img/10-voteup.png">
</p>

Good luck!
