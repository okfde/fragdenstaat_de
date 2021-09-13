import * as vega from 'vega';
import { expressionInterpreter } from 'vega-interpreter';
import embed from 'vega-embed';

class CSPVegaView extends vega.View {
  constructor (runtime, opt) {
    opt.expr = expressionInterpreter
    super(runtime, opt);
  }
}

Array.from(document.querySelectorAll('[data-vegachart]')).forEach((el) => {
  let spec
  if (el.dataset.vegachartdata) {
    spec = JSON.parse(el.dataset.vegachartdata)
  } else {
    spec = JSON.parse(document.getElementById(el.dataset.vegachart).textContent);
  }
  if (!spec.data.url && !spec.data.values) {
    let data = JSON.parse(document.getElementById(el.dataset.vegachart + '_data').textContent);
    spec.data = {"values": data}
  }
  // Slightly smaller than container
  spec.width = Math.floor(el.clientWidth * 4/5)

  embed(el, spec, {
    viewClass: CSPVegaView,
    ast: true
  })
})
