/**
 * Defines externs for Firebase Auth.
 */
const firebase = {
  auth: function () {},
};

/**
 * Creates Google provider.
 * @constructor
 */
firebase.auth.GoogleAuthProvider = function() {};

/**
 * Triggers callback on state change.
 * @param {!Object} callback
 */
firebase.onAuthStateChanged = function(callback) {};

/**
 * Initializes Firebase ppp.
 * @param {!Object} config
 */
firebase.initializeApp = function(config) {};

/**
 * Creates new database connection instance.
 */
firebase.database = function() {};


firebase.database.ServerValue = {};


firebase.database.ServerValue.TIMESTAMP = null;
