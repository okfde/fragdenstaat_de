CKEDITOR.plugins.add('figureblockquote', {
  requires: 'widget',
  icons: 'figureblockquote',
  init: function (editor) {
    editor.ui.addButton('figureblockquote', {
      label: 'Blockquote with caption',
      command: 'figureblockquote'
    })

    editor.widgets.add('figureblockquote', {
      template:
        '<figure class="blockquote-figure"><blockquote class="blockquote"></blockquote><figcaption class="blockquote-footer"></figcaption></figure>',
      editables: {
        quote: {
          selector: 'blockquote'
        },
        caption: {
          selector: 'figcaption',
          allowedContent: {
            a: {
              attributes: { href: true },
              requiredAttributes: { href: true }
            },
            br: true,
            em: true,
            strong: true
          }
        }
      },
      allowedContent: {
        blockquote: {
          classes: { blockquote: true },
          requiredClasses: { blockquote: true }
        },
        figcaption: {
          classes: { 'blockquote-footer': true },
          requiredClasses: { 'blockquote-footer': true }
        },
        figure: {
          classes: { 'blockquote-figure': true },
          requiredClasses: { 'blockquote-figure': true }
        }
      },
      requiredContent: {
        blockquote: {
          classes: { blockquote: true },
          requiredClasses: { blockquote: true }
        },
        figcaption: {
          classes: { 'blockquote-footer': true },
          requiredClasses: { 'blockquote-footer': true }
        },
        figure: {
          classes: { 'blockquote-figure': true },
          requiredClasses: { 'blockquote-figure': true }
        }
      },
      upcast: function (element) {
        return element.name == 'figure' && element.hasClass('blockquote-figure')
      }
    })
  },
  onLoad: function () {
    CKEDITOR.addCss(
      'figure.blockquote-figure { margin: 1rem auto 0.5rem; padding: 1rem 2rem 0; width: 100%; background-color: var(--gray-100); }' +
        'figure.blockquote-figure > blockquote > p {border-left: 4px solid var(--gray-400); padding: 0.5rem 0 0.5rem 1rem; font-size: 1.3rem; margin: 0;}'
    )
  }
})
