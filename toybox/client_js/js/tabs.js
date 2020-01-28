goog.module('toybox.tabs.main');


const forms = goog.require('toybox.forms.main');
const tmplMain = goog.require('toybox.templates.main');


/**
 * Scrolls page to the top.
 */
function scrollIntoView() {
  $('body')[0].scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  });
}


/**
 * Shows error message on the status panel.
 * @param {!Object} serverError A server error.
 * @param {!Object} status Apanel that will receive text.
 */
function businessError(serverError, status) {
  if (serverError) {
    status.text(serverError.message);
    status.show();
  }
}


/**
 * Collection of tabs.
 * @param {!Object} view A view that holds the tabs.
 * @param {!Object} user A current user.
 * @constructor
 */
function Tabs(view, user) {
  const items_ = {};

  function addNavBarAction(actions, tab, active) {
    const li = $('<li/>', {
      class: tab.nameClass + (active ? ' active' : ''),
    });
    const a = $('<a/>', {
      text: tab.title,
      href: '#',
    });

    a.on('click', function() {
      view.open(tab.name);
      return false;
    });

    li.append(a);
    return li;
  }

  function initNavBarActions(panel, activeTab) {
    const actions = panel.find('.a120-navbar-actions');
    actions.empty();

    for (var name in items_) {
      let tab = items_[name];
      let canView = !tab.canView || tab.canView();
      let canShow = !tab.canShowInMenu || tab.canShowInMenu();

      if (canView && canShow) {
        actions.append(addNavBarAction(actions, tab, activeTab.name == name));
      }
    }
  }

  function initNavBar(panel, tab) {
    const photo = panel.find('.a120-user-photo');
    photo.attr('src', user.photoURL);
    photo.attr('title', user.displayName + '\n(' + user.email + ')');

    const actionSignOut = panel.find('.a120-action-sign-out');
    actionSignOut.on('click', function() {
      view.getContext().signOut();
    });

    initNavBarActions(panel, tab);
  }

  /**
   * Finds tab class.
   * @param {?Object} name A hash, that represents the tab, aka "#home".
   * @return {!Object} A tab object corresponding to the name
   */
  function getTargetTab(name) {
    let tab = null;
    if (name && name in items_) {
      tab = items_[name];
      let canView = !tab.canView || tab.canView();
      if (canView) {
        return tab;
      }
    }

    if (registrationTab.canView()) {
      return registrationTab;
    }

    return homeTab;
  }

  this.open = function (panel, container, tabName) {
    const tab = getTargetTab(tabName);
    const content = tab.init();

    initNavBar(panel, tab);
    container.empty();
    container.append(content);

    view.getContext().emitEvent('activateTab: ' + tab.name, null);

    // update window location history;
    // temporarily disconnect window.window.onpopstate since
    // setting location triggers it, causing re-entrant call
    const oldHandler = window.onpopstate;
    try {
      window.onpopstate = null;
      window.location.hash = tab.name.substring(1);
    } finally {
      window.onpopstate = oldHandler;
    }
  };

  function register(tab) {
    if (tab.name in items_) {
      throw 'Already registered: ' + tab.name;
    }
    tab.nameClass = 'a120-action-hash-' + tab.name.substring(1);
    items_[tab.name] = tab;
  }

  const registrationTab = new RegistrationTab(view, user);
  const homeTab = new HomeTab(view, user);
  const postsTab = new PostsTab(view, user);
  const membersTab = new MembersTab(view, user);
  const settingsTab = new SettingsTab(view, user);
  const adminTab = new AdminTab(view, user);

  // order here defines the order of buttons in the nav bar
  register(homeTab);
  register(postsTab);
  register(membersTab);
  register(registrationTab);
  register(settingsTab);
  register(adminTab);
}


/**
 * Home tab.
 * @constructor
 * @param {!Object} view A view that holds current user home page.
 * @param {!Object} user A current user.
 */
function HomeTab(view, user) {
  this.name = '#home';
  this.title = 'Home';

  this.canView = function() {
    return user.isRegistered();
  };

  this.init = function() {
    const tab = tmplMain.renderAsElement('.tabHome');
    return tab;
  };
}


/**
 * Posts tab.
 * @constructor
 * @param {!Object} view A view that holds the member directory.
 * @param {!Object} user A current user.
 */
function PostsTab(view, user) {
  this.name = '#posts';
  this.title = 'Posts';

  this.canView = function() {
    return user.isRegistered();
  };

  function renderPost(container, post, tab) {
    const panel = tmplMain.renderAsElement('.panelPost');
    const status = panel.find('.a120-post-action-status');
    status.hide();

    panel.find('.a120-post-content').text(post.data.content);

    const total = panel.find('.a120-votes-total');

    function updatePost(post) {
      total.text('' + post.votes_total);
      voteUp.removeClass('a120-vote-active');
      voteDown.removeClass('a120-vote-active');
      if (post.my_vote_value == 1) {
        voteUp.addClass('a120-vote-active');
      }
      if (post.my_vote_value == -1) {
        voteDown.addClass('a120-vote-active');
      }
    }

    const deleteBtn = panel.find('.a120-btn-delete-post');
    deleteBtn.on('click', function() {
      let result = confirm('Delete this post?');
      if (result != true) {
        return false;
      }

      status.hide();
      view.getContext().getAPI().deletePost(
          {
            'uid': post.uid,
          },
          function(response) {
            view.getContext().showFlash('Deleted.');
            viewAllPosts(container);
          },
          function(serverError) {
            view.getContext().showFlash('Error.');
            businessError(serverError, status);
          }
      );

      return false;
    });
    if (!post.can_delete) {
      deleteBtn.hide();
    }

    function voteValue(value, message) {
      status.hide();
      view.getContext().getAPI().voteValue(
          {
            'uid': post.uid,
            'value': value,
          },
          function(response) {
            view.getContext().showFlash(message);
            updatePost(response.result);
          },
          function(serverError) {
            view.getContext().showFlash('Error.');
            businessError(serverError, status);
          }
      );
    }

    const voteUp = panel.find('.a120-btn-vote-up');
    voteUp.on('click', function() {
      voteValue(1, 'Voted up.');
      return false;
    });

    const voteDown = panel.find('.a120-btn-vote-down');
    voteDown.on('click', function() {
      voteValue(-1, 'Voted down.');
      return false;
    });

    updatePost(post);
    panel.append($('<hr>'));

    tab.append(panel);
  }

  function processNewPostForm(form, errors) {
    const post = {
      content: form.find('.a120-post-content').val(),
    };

    if (!post.content) {
      errors.push('Content is required.');
    }

    return post;
  }

  function viewNewPostForm(container) {
    const form = tmplMain.renderAsElement('.formNewPost');
    const status = form.find('.a120-save-status');
    status.hide();

    const cancel = form.find('.a120-btn-cancel');
    cancel.on('click', function(){
      viewAllPosts(container);
      return false;
    });

    const save = form.find('.a120-btn-save');
    save.on('click', function(){
      status.empty();
      status.hide();

      // construct profile from form data
      const errors = [];
      const post = processNewPostForm(form, errors);

      // validate errors
      if (errors.length) {
        for (var i=0; i<errors.length; i++) {
          status.append($('<p/>', {
            text: errors[i],
          }));
        }
        status.show();
        return false;
      }

      // submit
      view.getContext().getAPI().insertNewPost(
          post,
          function(response) {
            view.getContext().showFlash('Posted.');
            viewAllPosts(container);
          },
          function(serverError) {
            view.getContext().showFlash('Error.');
            businessError(serverError, status);
          }
      );
    });

    render(container, form);
  }

  function viewAllPosts(container) {
    const tab = tmplMain.renderAsElement('.tabPosts');
    view.getContext().getAPI().listPosts(function(posts) {
      if (!posts || posts.length == 0) {
        tab.append($('<p>no public posts</p>'));
        return;
      }

      // render all posts
      for (let i=0; i<posts.length; i++) {
        renderPost(container, posts[i], tab);
      }
    });

    const newPost = tab.find('.a120-btn-new-post');
    newPost.on('click', function() {
      viewNewPostForm(container);
      return false;
    });

    render(container, tab);
  }

  function render(container, content){
    container.empty();
    container.append(content);
    scrollIntoView();
  }

  this.init = function(){
    const container = $('<div/>');
    viewAllPosts(container);
    return container;
  };
}


/**
 * Members tab.
 * @constructor
 * @param {!Object} view A view that holds the member directory.
 * @param {!Object} user A current user.
 */
function MembersTab(view, user) {
  this.name = '#members';
  this.title = 'Members';

  this.canView = function() {
    return user.isRegistered();
  };

  this.init = function(){
    const tab = tmplMain.renderAsElement('.tabMembers');
    const visibility_public = view.getContext().app.schema.profile.visibility.keys.public;

    view.getContext().getAPI().listMembers(function(members) {
      if (!members || members.length == 0) {
        tab.append($('<p>no public members</p>'));
        return;
      }

      function byDisplayName(a, b) {
        a = a.registration;
        b = b.registration;
        if (!a || !b) {
          return 1;
        }

        a = a.displayName;
        b = b.displayName;

        if (a < b)
          return -1;
        if (a > b)
          return 1;
        return 0;
      }

      members.sort(byDisplayName);
      for (var i=0; i<members.length; i++) {
        let member = members[i];
        let profile = member.profile;
        let registration = member.registration;

        // don't show unregistered
        if (!registration) {
          continue;
        }

        // don't show users without profile unless admin role
        if (!profile) {
          if (!user.isAdmin()) {
            continue;
          }
          profile = {};
        }

        let panel = tmplMain.renderAsElement('.panelMember');
        let img = panel.find('.a120-member-photo');
        let about = panel.find('.a120-member-about');

        function addAbout(name, value) {
          about.append($('<p/>', {
            text: '' + name + ': ' + (value ? value : '<NOT PROVIDED>'),
          }));
        }

        if (profile.visibility != visibility_public) {
          panel.addClass('a120-member-container-private');
          about.append($('<span/>', {
            class: 'label label-default pull-right',
            text: 'UNLISTED',
          }));
        }

        img.attr('src', registration.photoURL);
        img.attr('title',
                 registration.displayName + '\n(' + registration.email + ')' + (
                     profile.pronouns ? '\n' + profile.pronouns : ''));
        img.tooltip({});

        about.append($('<p/>', {
          class: 'a120-member-name',
          text: '' + registration.displayName.split(' ')[0],
        }));

        addAbout('Title',profile.title);
        addAbout('Location', profile.location);
        addAbout('About', profile.about);

        tab.append(panel);
      }
    });

    return tab;
  };
}


/**
 * Settings tab.
 * @constructor
 * @param {!Object} view A view that holds current user settings.
 * @param {!Object} user A current user.
 */
function SettingsTab(view, user) {
  this.name = '#settings';
  this.title = 'Settings';

  this.canView = function() {
    return user.isRegistered();
  };

  function getAttr(name) {
    if (user.settings &&
        user.settings.profile &&
        name in user.settings.profile
    ) {
      return user.settings.profile[name];
    }
    return null;
  }

  function renderGoogleAccountProfile(tab) {
    const name = tab.find('.a120-profile-name');
    name.text(user.displayName);

    const email = tab.find('.a120-profile-email');
    email.text(user.email);

    const photo = tab.find('.a120-profile-photo');
    photo.attr('src', user.photoURL);
    photo.attr('title', user.displayName + '\n(' + user.email + ')');
  }

  function renderUserProfile(tab) {
    const visibilitySelect = new forms.Select(
        view.getContext().app.schema.profile.visibility.values);
    visibilitySelect.setValue(getAttr('visibility'));
    const visibility = tab.find('.a120-profile-visibility');
    visibility.text(visibilitySelect.getText());

    const pronouns = tab.find('.a120-profile-pronouns');
    pronouns.text(getAttr('pronouns'));

    const title = tab.find('.a120-profile-title');
    title.text(getAttr('title'));

    const location = tab.find('.a120-profile-location');
    location.text(getAttr('location'));

    const about = tab.find('.a120-profile-about');
    about.text(getAttr('about'));

    const tagsHelper = new forms.OptionsSet(
        view.getContext().app.schema.profile.tags);
    tagsHelper.setKeys(getAttr('tags'), null);

    const tags = tab.find('.a120-profile-tags');
    tags.text(tagsHelper.getTexts(null).join(', '));
  }

  function renderUserProfileForm(form) {
    const visibility = new forms.Select(
        view.getContext().app.schema.profile.visibility.values);
    visibility.init(form.find('.a120-profile-visibility'));
    visibility.setValue(getAttr('visibility'));

    const pronouns = form.find('.a120-profile-pronouns');
    pronouns.val(getAttr('pronouns'));

    const title = form.find('.a120-profile-title');
    title.val(getAttr('title'));

    const location = form.find('.a120-profile-location');
    location.val(getAttr('location'));

    const about = form.find('.a120-profile-about');
    about.text(getAttr('about'));

    const tagsHelper = new forms.OptionsSet(
        view.getContext().app.schema.profile.tags);
    const tags = form.find('.a120-profile-tags');
    tagsHelper.init(tags);
    tagsHelper.setKeys(getAttr('tags'), tags);
  }

  /**
   * Client-side validation of user profile.
   * @param {!Object} form Form that holds profile data.
   * @param {!Object} errors An aray where we can push validation errors.
   * @return {!Object} A dict of profile data; partially valid if errors.
   */
  function processUserProfileForm(form, errors) {
    const tags = new forms.OptionsSet(
        view.getContext().app.schema.profile.tags);

    const profile = {
      visibility: form.find('.a120-profile-visibility').val(),
      pronouns: form.find('.a120-profile-pronouns').val(),
      title: form.find('.a120-profile-title').val(),
      location: form.find('.a120-profile-location').val(),
      about: form.find('.a120-profile-about').val(),
      tags: tags.getKeys(form),
    };

    if (!profile.visibility) {
      errors.push('Visibility is required.');
    }
    if (!profile.title) {
      errors.push('Title is required.');
    }
    if (!profile.location) {
      errors.push('Location is required.');
    }

    return profile;
  }

  function checkSame(obj1, obj2) {
    return (obj1 && obj2) && JSON.stringify(
        obj1, Object.keys(obj1).sort()
        ) == JSON.stringify(
            obj2, Object.keys(obj2).sort()
        );
  }

  function editUserProfile(container) {
    const form = tmplMain.renderAsElement('.formUserProfile');
    const status = form.find('.a120-save-status');
    status.hide();

    renderUserProfileForm(form);

    const cancel = form.find('.a120-btn-cancel');
    cancel.on('click', function(){
      viewUserProfile(container);
      return false;
    });

    const save = form.find('.a120-btn-save');
    save.on('click', function(){
      status.empty();
      status.hide();

      // construct profile from form data
      const errors = [];
      const profile = processUserProfileForm(form, errors);

      // cancel if no changes
      if (user.settings && checkSame(profile, user.settings.profile)) {
        status.text('Nothing changed.');
        status.show();
        return false;
      }

      // validate errors
      if (errors.length) {
        for (var i=0; i<errors.length; i++) {
          status.append($('<p/>', {
            text: errors[i],
          }));
        }
        status.show();
        return false;
      }

      // submit update to server
      view.getContext().getAPI().updateCurrentUserProfile(
          profile,
          function(response) {
            view.getContext().showFlash('Saved.');
            viewUserProfile(container);
          },
          function(serverError) {
            view.getContext().showFlash('Error.');
            businessError(serverError, status);
          }
      );

      return false;
    });

    render(container, form);
  }

  function viewUserProfile(container) {
    const tab = tmplMain.renderAsElement('.tabSettings');
    renderGoogleAccountProfile(tab);
    renderUserProfile(tab);

    const edit = tab.find('.a120-btn-edit-profile');
    edit.on('click', function(){
      editUserProfile(container);
    });

    render(container, tab);
  }

  function render(container, content){
    container.empty();
    container.append(content);
    scrollIntoView();
  }

  this.init = function(){
    const container = $('<div/>');
    viewUserProfile(container);
    return container;
  };
}

/**
 * Admin tab.
 * @constructor
 * @param {!Object} view A view that holds admin information.
 * @param {!Object} user A current user.
 */
function AdminTab(view, user) {
  this.name = '#admin';
  this.title = 'Admin';

  this.canView = function() {
    return user.isAdmin();
  };

  function impersonationBtn(container, tab) {
    let newRoles = user.getImpersonationRoles();
    let caption = 'Impersonate';
    if (newRoles) {
      caption = 'Impersonating [' + newRoles.join(',') + ']';
    } else {
      newRoles = [];
    }

    const btn = $('<a/>', {
      class: 'btn btn-primary a120-tab-main-btn',
      text: caption,
    });

    btn.on('click', function() {
      let roles = prompt(
          'Enter comma delimited list of roles (n spaces) or ' +
          'leave empty to stop impersonation:',
          newRoles.join(','));
      if (roles != null) {
        user.setImpersonationRoles(roles.split(','));
        renderAdminView(container);
      }
    });

    tab.append(btn);
    tab.append($('<hr class="a120-clear">'));
  }

  function renderAdminView(container) {
    const tab = tmplMain.renderAsElement('.tabAdmin');
    const pre_style = 'white-space: pre-wrap; font-size: 75%;';

    impersonationBtn(container, tab);

    tab
        .append($('<p><b>Users Online</b>: </p>'))
        .append($('<pre class="a120-users-online">NA</pre>'));

    tab
        .append($('<p><b>Application Metadata</b>: </p>'))
        .append($('<pre/>', {
          style: pre_style,
          text: JSON.stringify(view.getContext().app, null, 4),
        }));

    tab
        .append($('<p><b>Server Metadata</b>: </p>'))
        .append($('<pre/>', {
          style: pre_style,
          text: JSON.stringify(view.getContext().server, null, 4),
        }));

    tab
        .append($('<p><b>User Metadata</b>: </p>'))
        .append($('<pre/>', {
          style: pre_style,
          text: JSON.stringify(user, null, 4),
        }));

    render(container, tab);
  }

  function render(container, content){
    container.empty();
    container.append(content);
    scrollIntoView();
  }

  this.init = function(){
    const container = $('<div/>');
    renderAdminView(container);
    return container;
  };
}


/**
 * Settings tab.
 * @constructor
 * @param {!Object} view A view that holds the tabs.
 * @param {!Object} user A current user.
 */
function RegistrationTab(view, user) {
  this.name = '#registration';
  this.title = 'Registration';

  this.canShowInMenu = function() {
    return false;
  };

  this.canView = function() {
    return !user.isRegistered();
  };

  this.init = function () {
    const consent = tmplMain.renderAsElement('.userConsent');
    const email = consent.find('.a120-consent-email');
    const status = consent.find('.a120-consent-status');
    const submit = consent.find('.a120-consent-submit');

    email.text(user.email);
    status.hide();

    submit.on('click', function() {
      let all_checked = true;
      consent.find('input[type=checkbox]').each(function() {
        if (!this.checked) {
          all_checked = false;
        }
      });

      if (!all_checked) {
        status.text('You must accept all terms to continue.');
        status.show();
        return false;
      }

      view.getContext().getAPI().registerCurrentUser(function() {
        view.open(null);
      });
      return false;
    });

    return consent;
  };
}


exports.Tabs = Tabs;
