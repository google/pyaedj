goog.module('toybox.boot.main');


const appContextModule = goog.require('toybox.main');


/**
 * Starts the application.
 */
$(document).ready(function() {
  console.log('A120: PWA: app: loaded {' +
              JSON.stringify(window.location.href) + '}');
  appContextModule.start();
});
