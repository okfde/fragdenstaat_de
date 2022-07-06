/*
 * Copyright (c) 2013, Divio AG
 * Licensed under BSD
 * http://github.com/aldryn/aldryn-boilerplate-bootstrap3
 */

// #############################################################################
// CKEDITOR
/**
 * Default CKEDITOR Styles
 * Added within src/settings.py CKEDITOR_SETTINGS.stylesSet
 *
 * @module CKEDITOR
 */
/* global CKEDITOR */

CKEDITOR.allElements = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div'];
CKEDITOR.stylesSet.add('default', [
    /* Block Styles */
    // { 'name': 'Text Left', 'element': CKEDITOR.allElements, 'attributes': { 'class': 'text-left' }},
    // { 'name': 'Text Center', 'element': CKEDITOR.allElements, 'attributes': { 'class': 'text-center' }},
    // { 'name': 'Text Right', 'element': CKEDITOR.allElements, 'attributes': { 'class': 'text-right' }},
    // { 'name': 'Text Justify', 'element': CKEDITOR.allElements, 'attributes': { 'class': 'text-justify' }},
    // { 'name': 'Text NoWrap', 'element': CKEDITOR.allElements, 'attributes': { 'class': 'text-nowrap' }},

    { 'name': 'Link-Button Primary', 'element': 'a', 'attributes': { 'class': 'btn btn-primary' }},
    { 'name': 'Link-Button Success', 'element': 'a', 'attributes': { 'class': 'btn btn-success' }},
    { 'name': 'Link-Button Info', 'element': 'a', 'attributes': { 'class': 'btn btn-info' }},
    { 'name': 'Link-Button Warning', 'element': 'a', 'attributes': { 'class': 'btn btn-warning' }},
    { 'name': 'Link-Button Danger', 'element': 'a', 'attributes': { 'class': 'btn btn-danger' }},
    { 'name': 'Link-Button Light', 'element': 'a', 'attributes': { 'class': 'btn btn-light' }},
    { 'name': 'Link-Button Dark', 'element': 'a', 'attributes': { 'class': 'btn btn-dark' }},

    { 'name': 'Spacer', 'element': 'div', 'attributes': { 'class': 'mt-3 mb-3' }},

    { 'name': 'Text Lead', 'element': 'p', 'attributes': { 'class': 'lead' }},

    { 'name': 'Teaser', 'element': 'p', 'attributes': { 'class': 'teaser-intro' }},

    { 'name': 'List Unstyled', 'element': ['ul', 'ol'], 'attributes': { 'class': 'list-unstyled' }},
    { 'name': 'List Timeline', 'element': ['ul', 'ol'], 'attributes': { 'class': 'timeline' }},
    { 'name': 'List Inline', 'element': ['ul', 'ol'], 'attributes': { 'class': 'list-inline' }},
    { 'name': 'Horizontal Description', 'element': 'dl', 'attributes': { 'class': 'dl-horizontal' }},

    { 'name': 'Table', 'element': 'table', 'attributes': { 'class': 'table' }},
    { 'name': 'Table Responsive', 'element': 'table', 'attributes': { 'class': 'table-responsive' }},
    { 'name': 'Table Striped', 'element': 'table', 'attributes': { 'class': 'table-striped' }},
    { 'name': 'Table Bordered', 'element': 'table', 'attributes': { 'class': 'table-bordered' }},
    { 'name': 'Table Hover', 'element': 'table', 'attributes': { 'class': 'table-hover' }},
    { 'name': 'Table Condensed', 'element': 'table', 'attributes': { 'class': 'table-condensed' }},

    { 'name': 'Table Cell Active', 'element': ['tr', 'th', 'td'], 'attributes': { 'class': 'active' }},
    { 'name': 'Table Cell Success', 'element': ['tr', 'th', 'td'], 'attributes': { 'class': 'success' }},
    { 'name': 'Table Cell Warning', 'element': ['tr', 'th', 'td'], 'attributes': { 'class': 'warning' }},
    { 'name': 'Table Cell Danger', 'element': ['tr', 'th', 'td'], 'attributes': { 'class': 'danger' }},
    { 'name': 'Table Cell Info', 'element': ['tr', 'th', 'td'], 'attributes': { 'class': 'info' }},

    /* Inline Styles */
    { 'name': 'Text Primary', 'element': 'span', 'attributes': { 'class': 'text-primary' }},
    { 'name': 'Text Secondary', 'element': 'span', 'attributes': { 'class': 'text-secondary' }},
    { 'name': 'Text Success', 'element': 'span', 'attributes': { 'class': 'text-success' }},
    { 'name': 'Text Danger', 'element': 'span', 'attributes': { 'class': 'text-danger' }},
    { 'name': 'Text Warning', 'element': 'span', 'attributes': { 'class': 'text-warning' }},
    { 'name': 'Text Info', 'element': 'span', 'attributes': { 'class': 'text-info' }},
    { 'name': 'Text Light', 'element': 'span', 'attributes': { 'class': 'text-light bg-dark' }},
    { 'name': 'Text Dark', 'element': 'span', 'attributes': { 'class': 'text-dark' }},
    { 'name': 'Text Muted', 'element': 'span', 'attributes': { 'class': 'text-muted' }},
    { 'name': 'Text White', 'element': 'span', 'attributes': { 'class': 'text-white bg-dark' }},

    /* Div Styles */
    { 'name': 'Block Primary', 'element': 'div', 'attributes': { 'class': 'p-3 mb-2 bg-primary text-white' }},
    { 'name': 'Block Secondary', 'element': 'div', 'attributes': { 'class': 'p-3 mb-2 bg-secondary text-white' }},
    { 'name': 'Block Success', 'element': 'div', 'attributes': { 'class': 'p-3 mb-2 bg-success text-white' }},
    { 'name': 'Block Danger', 'element': 'div', 'attributes': { 'class': 'p-3 mb-2 bg-danger text-white' }},
    { 'name': 'Block Warning', 'element': 'div', 'attributes': { 'class': 'p-3 mb-2 bg-warning text-dark' }},
    { 'name': 'Block Info', 'element': 'div', 'attributes': { 'class': 'p-3 mb-2 bg-info text-white' }},
    { 'name': 'Block Light', 'element': 'div', 'attributes': { 'class': 'p-3 mb-2 bg-light text-dark' }},
    { 'name': 'Block Dark', 'element': 'div', 'attributes': { 'class': 'p-3 mb-2 bg-dark text-white' }},
    { 'name': 'Block White', 'element': 'div', 'attributes': { 'class': 'p-3 mb-2 bg-white bg-dark' }},

    { 'name': 'Pull Left', 'element': 'div', 'attributes': { 'class': 'pull-left' }},
    { 'name': 'Pull Right', 'element': 'div', 'attributes': { 'class': 'pull-right' }},

    { 'name': 'Blockquote Reverse', 'element': 'blockquote', 'attributes': { 'class': 'blockquote-reverse' }}
]);

/*
 * Extend ckeditor default settings
 * DOCS: http://docs.ckeditor.com/#!/api/CKEDITOR.dtd
 */
CKEDITOR.dtd.$removeEmpty.span = 0;

function addSlugId(el) {
    const innerText = el.children.filter(x => x.type == CKEDITOR.NODE_TEXT).map(x => x.value).join(" ")
    const slug = innerText.toLowerCase().replace(/[^-_0-9a-zA-Z]/g, '-');
    if ((!el.attributes.id) || (el.attributes.id == el.attributes['data-auto-id'])) {
        el.attributes.id = slug;
        el.attributes['data-auto-id'] = slug;
    }
}

CKEDITOR.on('instanceReady', function (evt) {
    evt.editor.dataProcessor.htmlFilter.addRules({
        elements: {
            h1: addSlugId,
            h2: addSlugId,
            h3: addSlugId,
        }
    });
});
