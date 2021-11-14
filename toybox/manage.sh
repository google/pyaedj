#!/bin/bash

# fail script on any error
set -e
clear
echo "Running ToyBox manage.sh"
echo ""


# specify target GCP project ID
readonly PROD_PROJECT="psimakov-pwa"

# extract action passed as argument
readonly ACTION="$*"

# define version
readonly VERSION="v-$(date '+%Y%m%d-%H%M%S')"

# whether to enable minified JavaScript debugging using source maps
readonly USE_JS_SOURCE_MAPS="TRUE"

# define location for build and test
MANAGE_HOME=~/toybox/manage
mkdir -p "$MANAGE_HOME"
LOG="$MANAGE_HOME/log.txt"
echo "New log started" > "$LOG"


# Python 3
PY_BIN="python3"

# JavaScript build home
JS_ENV_HOME="$MANAGE_HOME/js"
JS_BUNDLE="$JS_ENV_HOME/release/js/bundle.js"

# define top level directory
APP_DIR="$MANAGE_HOME/app"


# build and test Python 3
function build_and_test_py3 {
  echo "Running pip3 install"
  pip3 install -r "./server_py3/requirements.txt" &>> "$LOG"

  echo "Copying Python 3 sourcers into $APP_DIR/server"
  cp -r "./server_py3/" "$APP_DIR/" &>> "$LOG"

  echo "Running Python 3 tests"
  pushd "$APP_DIR/"
  $PY_BIN dao_test.py &>> "$LOG"
  $PY_BIN main_test.py &>> "$LOG"
  popd
}

function build_and_test_js {
  rm -rf "$JS_ENV_HOME"
  mkdir -p "$JS_ENV_HOME"
  mkdir -p "$JS_ENV_HOME/externs"

  echo "Getting externs"
  curl -o "$JS_ENV_HOME/externs/jquery.js" \
    https://raw.githubusercontent.com/google/closure-compiler/master/contrib/externs/jquery-1.9.js &>> "$LOG"

  echo "Building JavaScript environment at $JS_ENV_HOME"
  curl -o "$JS_ENV_HOME/compiler.zip" \
    https://dl.google.com/closure-compiler/compiler-20191027.zip &>> "$LOG"
  unzip -d "$JS_ENV_HOME" "$JS_ENV_HOME/compiler.zip" &>> "$LOG"

  echo "Compiling JavaScript into $JS_BUNDLE"
  java -jar "$JS_ENV_HOME"/closure-compiler-v20191027.jar \
    --js_output_file="$JS_BUNDLE" \
    --externs "$JS_ENV_HOME/externs/jquery.js" \
    --externs client_js/js/firebase_auth_externs.js \
         --js client_js/js/firebase_auth.js \
         --js client_js/js/server.js \
         --js client_js/js/signal.js \
         --js client_js/js/boot.js \
         --js client_js/js/forms.js \
         --js client_js/js/templates.js \
         --js client_js/js/tabs.js \
         --js client_js/js/main.js \
    --compilation_level=SIMPLE \
    --formatting=PRINT_INPUT_DELIMITER \
    --create_source_map="$JS_BUNDLE.map"
}

function prepare_static_assets {
  echo "Copying static assets into $APP_DIR"

  mkdir -p "$APP_DIR/static/css/"
  mkdir -p "$APP_DIR/static/img/"
  mkdir -p "$APP_DIR/static/js/"

  # copy over original files
  cp -f ./client_js/index.html "$APP_DIR/static/"
  cp ./client_js/css/*.* "$APP_DIR/static/css/"
  cp ./client_js/img/*.* "$APP_DIR/static/img/"

  # prepare source maps if needed
  if [ "$USE_JS_SOURCE_MAPS" ]; then
    echo "Enabling JavaScript source-maps debugging" >> $LOG
    printf "\n\n//# sourceMappingURL=/js/bundle.js.map" >> $JS_BUNDLE
    mkdir -p "$APP_DIR/static/js/client_js/js/"
    cp ./client_js/js/*.js "$APP_DIR/static/js/client_js/js/"
  else
    rm -r "$JS_BUNDLE.map"
  fi

  # copy over compiled JavaScript bundle
  cp "$JS_ENV_HOME"/release/js/*.* "$APP_DIR/static/js/"
}

# build and test our project
function build_and_test {
  rm -rf "$MANAGE_HOME"
  echo "Logging into $LOG"

  build_and_test_js
  build_and_test_py3
  prepare_static_assets
}


# execute action
if [[ "$ACTION" == "run" ]]; then
  build_and_test
  echo "Running locally in $APP_DIR"
  export GOOGLE_CLOUD_PROJECT="$PROD_PROJECT"
  pushd "$APP_DIR/"
  $PY_BIN main.py
  popd
  exit 0
fi


# execute action
if [[ "$ACTION" == "deploy" ]]; then
  build_and_test
  echo "Deploying as $VERSION to $PROD_PROJECT from $PWD"
  gcloud app deploy \
      "$APP_DIR/app.yaml" \
      --no-promote \
      --project "$PROD_PROJECT" \
      --version "$VERSION"
  exit 0
fi


# print help text and list of actions
echo ""
echo "Usage:"
echo "   bash manage.sh {command}"
echo ""
echo "Valid commands are:"
echo "   [run, deploy]"
echo ""
exit 1
