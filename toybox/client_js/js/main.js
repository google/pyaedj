goog.module('toybox.main');


const firebaseModule = goog.require('toybox.firebase_auth.main');
const serverModule = goog.require('toybox.server.main');
const signalModule = goog.require('toybox.signal.main');
const tabs = goog.require('toybox.tabs.main');
const tmplMain = goog.require('toybox.templates.main');


/* <a120-pwa:config> */
const firebaseAppConfig = {
    apiKey: "AIzaSyD0OLPdWZ0o1bIzgD5LwKv_G20ULMX1L9A",
    authDomain: "psimakov-pwa.firebaseapp.com",
    databaseURL: "https://psimakov-pwa.firebaseio.com",
    projectId: "psimakov-pwa",
    storageBucket: "psimakov-pwa.appspot.com",
    messagingSenderId: "1055904220857",
};

const firebasePresence = true;

const signalConfig = {
    'client-id': 'test',
    'channel-id': 'web',
    'app-id': '//experimental/users/psimakov/pwa/app',
};

const themeName = 'green';
/* </a120-pwa:config> */


/**
 * A facade to accessing window.sessionStorage or window.localStorage as object.
 * @constructor
 */
function ClientStorage(storage) {

  this.set = function(name, value) {
    if (!storage.pwa) {
      storage.setItem('pwa', '{}');
    }
    let obj = JSON.parse(storage.pwa);
    obj[name] = value;
    storage.setItem('pwa', JSON.stringify(obj));
  };

  this.get = function(name) {
    if (!storage.pwa) {
      return null;
    }
    let obj = JSON.parse(storage.pwa);
    return obj[name];
  };

}

/**
 * A floating message that shows result of an action: "Added", "Saved".
 * @constructor
 */
function FlashMessage() {
  const delayShowForMillis = 500;
  const showForMillis = 7 * 1000;

  const message = $('.a120-flash-message');
  const content = message.find('.a120-flash-message-content');

  message.hide();

  let timeout = null;

  this.show = function(text) {
    content.text(text);
    message.hide();

    if (timeout) {
      clearTimeout(timeout);
    }

    timeout = setTimeout(function() {
      message.show();
      timeout = setTimeout(function() {
        message.hide();
        timeout = null;
      }, showForMillis);
    }, delayShowForMillis);
  };

}


/**
 * A facade to accessing our API server.
 * @constructor
 * @param {!Object} ctx Context proving the API.
 * @param {!Object} user A current user.
 * @param {function(!Object)} onUserChange A callback for current user updates.
 */
function API(ctx, user, onUserChange){

  const server = serverModule.init({
    //
    // Uncomment the line below for local debugging against live server.
    // url: 'https://psimakov-pwa.appspot.com',
    //
    authHeadersProvider: ctx.firebase.withRequestAuthHeaders,
  });

  function updateAppSchema(response) {
    if (response.app) {
      ctx.app = response.app;
    }
    if (response.server) {
      ctx.server = response.server;
    }
  }

  function asValidationError(error) {
    //
    // inspect potential REST API errors here; if they are from
    // our server -- forward them to the caller for handling
    //
    try {
      const response = error[0].responseText;
      if (response.indexOf(')]}\'\n') == 0) {
        const unprefixed = response.substr(5);
        const parsed = JSON.parse(unprefixed);
        if (parsed.origin == 'google3.area120.common.pwa.server') {
          return parsed;
        }
      }
    } catch (parseError) { }
    return null;
  }

  this.checkWhoAmI = function(callback) {
    ctx.loading.show('checking account status');

    server.invoke(
        '/api/rest/v1/whoami', 'GET', null,
        function (response){
          ctx.loading.hide();
          updateAppSchema(response);
          callback(response.user);
        },
        function (error) {
          ctx.loading.hide();
          ctx.handleError(error);
        },
    );
  };

  this.listMembers = function(callback) {
    ctx.loading.show('loading members');

    server.invoke(
        '/api/rest/v1/members', 'GET', null,
        function (response){
          ctx.loading.hide();
          updateAppSchema(response);
          callback(response.result);
        },
        function (error) {
          ctx.loading.hide();
          ctx.handleError(error);
        },
    );
  };

  this.listPosts = function(callback) {
    ctx.loading.show('loading posts');

    server.invoke(
        '/api/rest/v1/posts', 'GET', null,
        function (response){
          ctx.loading.hide();
          updateAppSchema(response);
          callback(response.result);
        },
        function (error) {
          ctx.loading.hide();
          ctx.handleError(error);
        },
    );
  };

  this.registerCurrentUser = function(callback) {
    ctx.loading.show('registering new user');

    server.invoke(
        '/api/rest/v1/registration', 'PUT', {
          settings_etag: user['settings_etag'],
        },
        function (response){
          ctx.loading.hide();
          updateAppSchema(response);
          onUserChange(response.user);
          callback();
        },
        function (error) {
          ctx.loading.hide();
          ctx.handleError(error);
        },
    );
  };

  function handleSuccess(response, onsuccess) {
    ctx.loading.hide();
    updateAppSchema(response);
    onUserChange(response.user);
    onsuccess(response);
  }

  function handleError(error, onerror) {
    ctx.loading.hide();
    const validationError = asValidationError(error);
    if (validationError) {
      onerror(validationError);
    } else {
      onerror(null);
      ctx.handleError(error);
    }
  }

  this.insertNewPost = function(post, onsuccess, onerror) {
    ctx.loading.show('saving your post');

    server.invoke(
        '/api/rest/v1/posts', 'PUT', {
          post: JSON.stringify(post),
        },
        function (response){
          handleSuccess(response, onsuccess);
        },
        function (error) {
          handleError(error, onerror);
        },
    );
  };

  this.deletePost = function(post, onsuccess, onerror) {
    ctx.loading.show('deleting your post');

    server.invoke(
        '/api/rest/v1/posts', 'POST', {
          post: JSON.stringify(post),
        },
        function (response){
          handleSuccess(response, onsuccess);
        },
        function (error) {
          handleError(error, onerror);
        },
    );
  };

  this.voteValue = function(vote, onsuccess, onerror) {
    ctx.loading.show('voting on post');

    server.invoke(
        '/api/rest/v1/votes', 'PUT', {
          vote: JSON.stringify(vote),
        },
        function (response){
          handleSuccess(response, onsuccess);
        },
        function (error) {
          handleError(error, onerror);
        },
    );
  };

  this.updateCurrentUserProfile = function(profile, onsuccess, onerror) {
    ctx.loading.show('updating user profile');

    server.invoke(
        '/api/rest/v1/profile', 'POST', {
          settings_etag: user['settings_etag'],
          profile: JSON.stringify(profile),
        },
        function (response){
          handleSuccess(response, onsuccess);
        },
        function (error) {
          handleError(error, onerror);
        },
    );
  };

}


/**
 * Floating status bar used for display of "busy" messages like:
 * "Loading", "Saving", etc. One message at a time.
 * @constructor
 */
function Loading() {
  const container = $('.a120-loading');
  const content = container.find('.a120-loading-content');
  const img = $('.a120-loading-img');

  let waitable = null;
  let active = true;

  /**
   * Starts progress and shows message with delay.
   */
  this.show = function(text) {
    active = true;

    content.text(text);
    img.show();

    waitable = setTimeout(function() {
      waitable = null;
      if (active) {
        container.show();
      }
    }, 2000);
  };

  /**
   * Stops progress and hides message.
   */
  this.hide = function() {
    if (waitable) {
      clearTimeout(waitable);
      waitable = null;
    }
    active = false;
    img.hide();
    container.hide();
  };

  /**
   * Stops progress and shows message (usually an error).
   */
  this.stop = function(text) {
    active = false;
    img.hide();
    content.text(text);
    container.show();
  };
}


/**
 * Broadcasts users online.
 * @constructor
 */
function UsersOnline() {
  let usersOnline = null;

  setInterval(function () {
    let text = 'NA';
    if (usersOnline) {
      text = '' + usersOnline;
    }
    $('.a120-users-online').text(text);
  }, 2000);

  this.onUsersOnline = function(count) {
    usersOnline = count;
  };
}


/**
 * Manages objects accessible to the entire application.
 * @constructor
 */
function AppContext() {
  const ctx_ = this;

  const sessionStorage = new ClientStorage(window.sessionStorage);

  // firebase
  if (firebasePresence) {
    firebaseAppConfig.onUsersOnline = new UsersOnline().onUsersOnline;
  }
  this.firebase = firebaseModule.init(firebaseAppConfig);

  // signal
  const signal = signalModule.init(signalConfig);

  // progress & message bar
  this.loading = new Loading();

  // current view
  let currentView = null;

  // this is Firebase user
  let currentUser = null;

  // the most recent app metadata
  this.app = null;

  // the most recent server metadata
  this.server = null;

  /**
   * Reference to currentActor is in all the child views. If we replace this
   * reference with a reference to a new updated instabce -- how will we update
   * the child views? We never replace const currentActor -- we repopulate it.
   * All views that had reference to currentActor still point to it, but it now
   * has very different data. We may provide local notifications to let views
   * know currentActor has changed, but we don't to now.
   */
  function replaceCurrentActor(newActor) {
    // copy newActor fields into currentActor
    for (let key in currentActor) {
      delete currentActor[key];
    }
    for (let key in newActor) {
      currentActor[key] = newActor[key];
    }

    /**
     * Sets impersonation roles for this user.
     * @param {?Object} roles New roles or null to remove impersonation.
     */
    currentActor.setImpersonationRoles = function(roles) {
      if (!currentActor.isAdmin()) {
        throw 'Only "admin" role can impersonate other roles.';
      }
      if (roles == '') {
        roles = null;
      }

      // validate roles
      if (roles) {
        for (let i=0; i<roles.length; i++) {
          let role = roles[i];
          if (!(role in ctx_.app.schema.user.role.keys)) {
            const error = 'Unknown role "' + role + '".';
            ctx_.loading.show(error);
            throw error;
          }
        }
      }

      sessionStorage.set('impersonationRoles', roles);
    };

    /**
     * Current impersonation roles set for this user.
     * @return {?Object} impersonation roles
     */
    currentActor.getImpersonationRoles = function() {
      let roles = sessionStorage.get('impersonationRoles');
      if (roles) {
        return roles;
      }
      return null;
    };

    /**
     * Roles applicable to this user considering user account and impersonation.
     * @return {?Object} impersonation roles
     */
    currentActor.getEffectiveRoles = function() {
      if (currentActor.getImpersonationRoles()) {
        return currentActor.getImpersonationRoles();
      }
      if (currentActor.roles) {
        return currentActor.roles;
      }
      return [];
    };

    currentActor.isRegistered = function() {
      return currentActor.settings && currentActor.settings.registered;
    };

    currentActor.isAdmin = function() {
      const targetRole = ctx_.app.schema.user.role.keys.admin;
      return currentActor.roles && (
          currentActor.roles.indexOf(targetRole) != -1);
    };

    currentActor.isModerator = function() {
      const targetRole = ctx_.app.schema.user.role.keys.moderator;
      return currentActor.getEffectiveRoles().indexOf(targetRole) != -1;
    };
  }

  // flash status message
  const flash = new FlashMessage();
  this.showFlash = function(text) {
    flash.show(text);
  };

  // this is our own user returned by our own server
  const currentActor = {};
  replaceCurrentActor({});

  // API helper class
  const api = new API(this, currentActor, replaceCurrentActor);

  this.getAPI = function() {
    return api;
  };

  this.emitEvent = function(name, value) {
    let text = 'A120: PWA: ' + name;
    if (value) {
      text += ' {' + JSON.stringify(value) + '}';
    }
    console.log(text);
    signal.emitEvent(null, {
      name: value,
    });
  };

  function enterView(viewClass, user) {
    ctx_.loading.show('loading ' + viewClass.viewName);

    currentView = new viewClass(ctx_, user);

    if (!currentView.canView()) {
      const msg = 'Access denied ' +
          'for user "' + (user ? user.email : 'anonymous') + '" ' +
          'to view "' + viewClass.viewName + '".';
      ctx_.emitEvent('viewAccessDenied', msg);
      throw msg;
    }
    ctx_.emitEvent('enterView: ' + viewClass.viewName,
                   (user ? user.email : 'anonymous'));

    currentView.open();
    ctx_.loading.hide();
  }

  function checkUserStatusAndEnterUserView(viewClass) {
    api.checkWhoAmI(function(user){
      if (user) {
        replaceCurrentActor(user);
      } else {
        replaceCurrentActor({});
      }
      if (user && user.roles.length > 0) {
        // user has valid roles; open default view
        enterView(viewClass, currentActor);
      } else {
        // user has no valid roles; open access denied view
        enterView(AccessDeniedView, currentActor);
      }
    });
  }

  this.userChanged = function(user) {
    ctx_.emitEvent('userChanged', (user ? user.email : 'anonymous'));

    // user >> null
    if (currentUser && !user) {
      // TODO(psimakov): allow new sign-in without location.reload()
      alert('Your session has expired.\nPlease sign-in again.');
      location.reload();
      return;
    }

    // user A >> user B
    if (currentUser && user && currentUser != user) {
      // unexpected; we expect userChaaged(null) first
      location.reload();
      return;
    }

    // null >> user
    currentUser = user;
    replaceCurrentActor({});
    if (currentUser) {
      ctx_.activateView(HomePageView);
    } else {
      ctx_.activateView(WelcomePageView);
    }
  };

  this.activateView = function (viewClass) {
    // close current view
    if (currentView) {
      ctx_.emitEvent('leaveView: ' + currentView.constructor.viewName,
                     (currentUser ? currentUser.email : 'anonymous'));
      currentView.close();
    }

    // enter new view
    if (currentUser) {
      checkUserStatusAndEnterUserView(viewClass);
    } else {
      enterView(viewClass, null);
    }
  };

  this.handleError = function(error) {
    ctx_.emitEvent('handleError', error);
    ctx_.loading.stop(JSON.stringify(error));
  };

  this.signIn = function () {
    ctx_.emitEvent('signIn', (currentUser ? currentUser.email : 'anonymous'));
    ctx_.firebase.signIn();
  };

  this.signOut = function () {
    ctx_.emitEvent('signOut', (currentUser ? currentUser.email : 'anonymous'));

    currentUser = null;
    replaceCurrentActor({});
    currentView = null;

    ctx_.firebase.unbind();
    ctx_.firebase.signOut();

    location.reload();
  };

  this.start = function (){
    // activate theme
    $('body').addClass('a120-theme');
    $('body').addClass('a120-theme-' + themeName);

    ctx_.emitEvent('appContext: started', null);

    ctx_.firebase.bind({
      onAuthStateChange: function(user) {
        ctx_.userChanged(user);
      },
      onAuthError: function(error) {
        ctx_.handleError(error);
      },
    });

    ctx_.showFlash('Ready.');
  };

  // watch and respond to back button
  window.onpopstate = function(event) {
    if (currentView && currentView.onPopState) {
      currentView.onPopState(event);
    }
  };
}


/**
 * Starts the application.
 * @return {!Object} New application context.
 */
AppContext.start = function() {
  const ctx = new AppContext();
  ctx.start();
  return ctx;
};


/**
 * Shows welcome page and lets user login.
 * @constructor
 * @param {!Object} ctx
 * @param {!Object} user
 */
function WelcomePageView(ctx, user) {
  const container = $('.a120-view-container');

  this.canView = function () {
    return true;
  };

  function initLoginPanel() {
    let loginPanel = tmplMain.renderAsElement('.loginPanel');
    loginPanel.find('.a120-login-btn button').on('click', function(){
      ctx.loading.show('waiting user login');
      loginPanel.hide();

      ctx.signIn();
    });
    return loginPanel;
  }

  this.open = function() {
    let loginPanel = initLoginPanel();

    container.empty();
    container.append(loginPanel);
  };

  this.close = function () {
    container.empty();
  };
}

WelcomePageView.viewName = 'Welcome Page';



/**
 * Shows access denied page if user is not allowed to access.
 * @constructor
 * @param {!Object} ctx
 * @param {!Object} user
 */
function AccessDeniedView(ctx, user) {
  const container = $('.a120-view-container');

  this.canView = function () {
    return true;
  };

  function initView() {
    let panel = tmplMain.renderAsElement('.accessDeniedPanel');
    panel.find('.a120-email').text(user.email);
    panel.find('.a120-message').text(user.status);
    panel.find('.a120-sign-out').on('click', function(){
      ctx.signOut();
    });
    return panel;
  }

  this.open = function() {
    let view = initView();

    container.empty();
    container.append(view);
  };

  this.close = function () {
    container.empty();
  };
}

AccessDeniedView.viewName = 'Access Denied';


/**
 * Shows application home page after login.
 * @constructor
 * @param {!Object} ctx
 * @param {!Object} user
 */
function HomePageView(ctx, user) {
  const view_ = this;
  const tabs_ = new tabs.Tabs(this, user);

  const container = $('.a120-view-container');

  this.getContext = function (){
    return ctx;
  };

  this.canView = function() {
    if (user) {
      return true;
    }
    return false;
  };

  function initView(tabName) {
    const panel = tmplMain.renderAsElement('.userHomePage');
    const container = panel.find('.a120-home-container');
    tabs_.open(panel, container, tabName);
    return panel;
  }

  this.open = function(tabName) {
    if (!tabName) {
      tabName = window.location.hash;
    }
    let view = initView(tabName);

    container.empty();
    container.append(view);
  };

  this.close = function () {
    container.empty();
  };

  this.onPopState = function(event) {
    view_.open(null);
  };

}

HomePageView.viewName = 'Home Page';


exports.start = AppContext.start;
