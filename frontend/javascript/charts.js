import 'vega'
import 'vega-lite'
import vegaEmbed from 'vega-embed'

const chartEmebds = document.querySelectorAll('[data-vegachart]')
if (chartEmebds.length > 0) {
  console.log('loaded vegaEmbed', vegaEmbed, 'for', chartEmebds)
  for (var i = 0; i < chartEmebds.length; i += 1) {
    let chartEmbed = chartEmebds[i]
    let spec = JSON.parse(unescape(chartEmbed.dataset.vegachart))
    vegaEmbed(chartEmbed, spec, {
      actions: false,
      renderer: 'svg'
    })
  }
}