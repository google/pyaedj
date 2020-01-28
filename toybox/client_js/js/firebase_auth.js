goog.module('toybox.firebase_auth.main');


/**
 * Initializes Firebase app.
 * @param {!Object} config
 * @return {!Object}
 */
exports.init = function(config) {

  // TODO(psimakov): add config validation

  function log(name, value) {
    let text = 'A120: PWA: ' + name;
    if (value) {
      text += ' {' + JSON.stringify(value) + '}';
    }
    console.log(text);
  }

  const HTTP_HEADER_NAME = 'A120-PWA-Authorization';
  const HTTP_HEADER_VALUE_PREFIIX = 'Firebase idToken ';

  firebase.initializeApp(config);
  const db = firebase.database();

  log('firebaseAuth: started', config.projectId);

  const callbacks = {
    onAuthStateChange: null,
    onAuthError: null,
    currentUser: null,
  };

  function trackPresence(user) {
    const amOnlineRef = db.ref('/.info/connected');  // system node
    const presenceList = db.ref('/users/online/');
    const isOnline = db.ref('/user/' + user.uid + '/is_online');
    const lastOnline = db.ref('/user/' + user.uid + '/last_online_timestamp');

    amOnlineRef.on('value', function(snap) {
      if (snap.val() === true) {

        // track presence of this user anonymously; adds value of true
        // to the server list of active users end removes it on disconnect
        const myPresence = presenceList.push();
        myPresence.onDisconnect().remove();
        myPresence.set(true);

        // track this user state presence; adds isOnline=True
        // to this server user object; resets to false on disconnect
        isOnline.onDisconnect().set(false);
        isOnline.set(true);

        // track this user last time onine; updates last active timestamp
        // on server user object on disconnect
        lastOnline.onDisconnect().set(firebase.database.ServerValue.TIMESTAMP);
      }
    });

    // subscribe to updates on number of users online
    if (config.onUsersOnline) {
      presenceList.on('value', function(snap) {
        config.onUsersOnline(snap.numChildren());
      });
    }
  }

  function onUserChange(user){
    // avoid multiple and recursive callbacks
    if (user && user == callbacks.currentUser) {
      return;
    }

    // configure presence service
    if (db && config.onUsersOnline) {
      log('firebasePresence: started', null);
      try {
        trackPresence(user);
      } catch(error) {
        log('firebasePresence: error', error);
      }
    } else {
      log('firebasePresence: inactive', null);
    }

    // propagate notification
    callbacks.currentUser = user;
    if (callbacks.onAuthStateChange) {
      var wrapped_user = null;
      if (user) {
        wrapped_user = {
          displayName: user.displayName,
          email: user.email,
          photoURL: user.photoURL,
        };
      }
      callbacks.onAuthStateChange(wrapped_user);
    }
  }

  function bind(args) {
    callbacks.onAuthStateChange = args.onAuthStateChange;
    callbacks.onAuthError = args.onAuthError;
    callbacks.currentUser = null;

    firebase.auth().onAuthStateChanged(function(user) {
      onUserChange(user);
    });
  }

  function unbind() {
    callbacks.onAuthStateChange = null;
    callbacks.onAuthError = null;
    callbacks.currentUser = null;
  }

  function signOut() {
    callbacks.currentUser = null;

    firebase.auth().signOut().then(function() {
      // no one cares
    }).catch(function(error) {
      callbacks.onAuthError(error);
    });
  }

  function signIn() {
    let provider = new firebase.auth.GoogleAuthProvider();

    // force account picker every time
    provider.setCustomParameters({
      prompt: 'select_account'
    });

    firebase.auth().signInWithPopup(provider).then(function(result) {
      onUserChange(result.user);
    }).catch(function(error) {
      if (callbacks.onAuthError) {
        callbacks.onAuthError(error);
      }
    });
  }

  function withRequestAuthHeaders(callback) {
    if (!callbacks.currentUser){
      throw 'No user in session.';
    }

    callbacks.currentUser.getIdToken().then(function(idToken) {
      const headers = {};
      headers[HTTP_HEADER_NAME] = HTTP_HEADER_VALUE_PREFIIX + idToken;
      callback(headers);
    });
  }

  return {
    bind: bind,
    unbind: unbind,
    signIn: signIn,
    withRequestAuthHeaders: withRequestAuthHeaders,
    signOut: signOut,
  };
};
