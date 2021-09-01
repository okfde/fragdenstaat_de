import * as vega from 'vega';
import { expressionInterpreter } from 'vega-interpreter';
import embed from 'vega-embed';

// Needed so ast: true works and sets expr as vega option
vega.expressionInterpreter = expressionInterpreter

Array.from(document.querySelectorAll('[data-vegachart]')).forEach((el) => {
  let spec = JSON.parse(el.dataset.vegachart)
  embed(el, spec, {
    ast: true // to make CSP compatible
  })
})
