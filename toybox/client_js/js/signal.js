goog.module('toybox.signal.main');


/**
 * Initializes Signal.
 * @param {!Object} config
 * @return {!Object}
 */
exports.init = function(config) {

  function emitEvent(id_token, payload) {
    const data = {};
    for (var key in config) {
      data[key] = config[key];
    }
    data['firebase-id-token'] = id_token;
    data['payload-json'] = JSON.stringify(payload);

    //
    // TODO(toyboxer): send signal to your server or Google Analytics
    //
  }

  return {
    emitEvent: emitEvent,
  };

};
