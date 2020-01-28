goog.module('toybox.forms.main');


/**
 * Settings tab.
 * @param {boolean} condition A condition being asserted.
 * @param {string} message An exception message if condition is not met.
 */
function assert(condition, message) {
  if (!condition) {
    throw message || 'Assertion failed';
  }
}


/**
 * Helps manage a collection of checkboxes.
 * @constructor
 * @param {!Object} allowedValues A dictionary of allowed values.
 */
function OptionsSet(allowedValues) {
  const that = this;
  const valueToInput = {};

  let keys = [];

  function byValue(a, b) {
    if (!a || !b) {
      return 1;
    }
    a = a.value;
    b = b.value;
    if (a < b)
      return -1;
    if (a > b)
      return 1;
    return 0;
  }

  function sortOnKeys(dict) {

    // convert dict to array
    const items = [];
    for (let key in dict) {
      items.push({
        key: key,
        value: dict[key],
      });
    }

    // sort
    items.sort(byValue);

    return items;
  }

  this.init = function(target) {
    const sorted = sortOnKeys(allowedValues);
    for (let i=0; i<sorted.length; i++) {
      let label = $('<label/>');
      var caption = document.createTextNode(sorted[i].value);
      let input = $('<input/>', {
        type: 'checkbox',
        class: 'a120-key-' + sorted[i].key,
      });

      label.append(input);
      label.append(caption);
      target.append(label);
      target.append($('<br>'));

      valueToInput[sorted[i].key] = input;
    }
  };

  this.getKeys = function(target) {
    if (!target) {
      return keys;
    }

    keys = [];
    for (let key in allowedValues) {
      let input = target.find('.a120-key-' + key);
      if (input.is(':checked')) {
        keys.push(key);
      }
    }

    return keys;
  };

  this.setKeys = function(newKeys, target) {
    if (!newKeys) {
      newKeys = [];
    }
    keys = [].concat(newKeys);

    if (target) {
      for (let i=0; i<keys.length; i++) {
        let input = target.find('.a120-key-' + keys[i]);
        input.prop('checked', true);
      }
    }
  };

  this.getTexts = function(target) {
    const items = [];
    const keys = that.getKeys(target);
    for (var i=0; i<keys.length; i++) {
      items.push(allowedValues[keys[i]]);
    }
    return items;
  };
}


/**
 * HTML <select> helper.
 * @constructor
 * @param {!Object} allowedValues A dictionary of allowed values.
 */
function Select(allowedValues) {
  const that = this;

  let select = null;
  let valueToOption = null;
  let currentValue = null;

  this.init = function(element) {
    assert(select == null, 'Already initialized.');
    select = element;

    valueToOption = {};

    let option = $('<option/>', {
      value: null,
      text: '<NOT SET>',
    });
    select.append(option);
    option.val(null);
    valueToOption[null] = option;

    for (var key in allowedValues) {
      let option = $('<option/>', {
        text: allowedValues[key],
      });
      select.append(option);
      option.val(key);
      valueToOption[key] = option;
    }

    that.setValue(currentValue);
  };

  this.setValue = function(value) {
    if (!value) {
      value = null;
    } else {
      assert(Object.keys(allowedValues).indexOf(value) != -1,
             'Bad value: ' + value);
    }
    currentValue = value;

    if (select) {
      valueToOption[currentValue].prop('selected', true);
    }
  };

  this.getValue = function() {
    if (select) {
      return select.val();
    }
    return currentValue;
  };

  this.getText = function() {
    return allowedValues[this.getValue()];
  };
}


exports.OptionsSet = OptionsSet;
exports.Select = Select;
