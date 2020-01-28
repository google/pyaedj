goog.module('toybox.server.main');


/**
 * Initializes Server.
 * @param {!Object} config
 * @return {!Object}
 */
exports.init = function(config) {

  const RPC_TIMEOUT = 5 * 1000;

  if (!config) {
    config = {};
  }

  // by default use window.location.origin as API server base URL
  if (!config.url) {
    config.url = window.location.origin;
  }

  function plainAJAX(url, method, data, headers, onsuccess, onerror) {
    $.ajax({
      dataType: 'html',
      contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
      url: url,
      data: data,
      type: method,
      timeout: RPC_TIMEOUT,
      beforeSend: function(request) {
        for (let name in headers) {
          request.setRequestHeader(name, headers[name]);
        }
      },
      success: function(response) {
        if (response.indexOf(')]}\'\n') != 0) {
          throw 'Bad response prefix.';
        }
        const unprefixed = response.substr(5);
        onsuccess(JSON.parse(unprefixed));
      },
      error: function(jqXHR, textStatus, errorThrown) {
        onerror([jqXHR, textStatus, errorThrown]);
      },
    });
  }

  function invoke(path, method, data, onsuccess, onerror) {
    const url = config.url + path;
    if (config.authHeadersProvider) {
      config.authHeadersProvider(function(headers) {
        plainAJAX(url, method, data, headers, onsuccess, onerror);
      });
    } else {
      plainAJAX(url, method, data, {}, onsuccess, onerror);
    }
  }

  function promiseInvoke(path, method, data) {
    return new Promise(function(resolve, reject) {
      invoke(path, method, data, function(response) {
        resolve(response);
      }, function (error) {
        reject(error);
      });
    });
  }

  return {
    invoke: invoke,
    promiseInvoke: promiseInvoke,
  };

};
