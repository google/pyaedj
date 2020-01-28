goog.module('toybox.templates.main');


function renderAsElement(templateClassName) {
  return $('.a120-templates').find(templateClassName).clone();
}


exports.renderAsElement = renderAsElement;
