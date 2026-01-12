import '../styles/vega.scss'

import { expressionInterpreter } from 'vega-interpreter'
import { Tooltip } from 'bootstrap'
import { mergeConfig } from 'vega'
import embed from 'vega-embed'

const backgroundColor = 'var(--bs-body-bg)'
const textColor = 'var(--bs-body-color)'
const mediumColor = 'var(--bs-secondary-bg)'

const colorTheme = {
  background: backgroundColor,

  view: {
    stroke: mediumColor
  },

  title: {
    color: textColor,
    subtitleColor: textColor
  },

  style: {
    'guide-label': {
      fill: textColor
    },
    'guide-title': {
      fill: textColor
    },
    cell: { stroke: null },
    'group-title': { font: 'Inter', fontSize: 14, fontWeight: 'bold' }
  },

  axis: {
    domainColor: mediumColor,
    gridColor: mediumColor,
    tickColor: mediumColor,
    labelColor: textColor,
    labelFont: 'Inter',
    labelFontSize: 12,
    titleFont: 'Inter',
    titleFontWeight: 'normal'
  }
}

const LOCALE = {
  de: {
    number: {
      decimal: ',',
      thousands: '.',
      grouping: [3],
      currency: ['', ' €']
    },
    time: {
      dateTime: '%A, der %e. %B %Y, %X',
      date: '%d.%m.%Y',
      time: '%H:%M:%S',
      periods: ['AM', 'PM'],
      days: [
        'Sonntag',
        'Montag',
        'Dienstag',
        'Mittwoch',
        'Donnerstag',
        'Freitag',
        'Samstag'
      ],
      shortDays: ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'],
      months: [
        'Januar',
        'Februar',
        'März',
        'April',
        'Mai',
        'Juni',
        'Juli',
        'August',
        'September',
        'Oktober',
        'November',
        'Dezember'
      ],
      shortMonths: [
        'Jan',
        'Feb',
        'Mrz',
        'Apr',
        'Mai',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Okt',
        'Nov',
        'Dez'
      ]
    }
  }
}

const bootstrapTooltipHandler = (handler, _event, item, value) => {
  let tooltip = Tooltip.getInstance(item._svg)
  let created = false
  if (!tooltip && value) {
    const html = `<dl>${Object.keys(value)
      .map((key) => `<dt>${key}</dt><dd>${value[key]}</dd>`)
      .join('')}</dl>`

    tooltip = Tooltip.getOrCreateInstance(item._svg, {
      html: true,
      sanitize: false,
      container: handler._el,
      placement: 'auto',
      title: html
    })
    created = true
  }
  if (value && created) {
    tooltip.show()
  }
}

document.querySelectorAll('[data-vegachart]').forEach((el) => {
  let spec
  if (el.dataset.vegachartdata) {
    spec = JSON.parse(el.dataset.vegachartdata)
  } else {
    spec = JSON.parse(document.getElementById(el.dataset.vegachart).textContent)
  }
  const hasData =
    (spec.data && (spec.data.url || spec.data.values)) || spec.datasets
  if (!hasData) {
    const data = JSON.parse(
      document.getElementById(el.dataset.vegachart + '_data').textContent
    )
    spec.data = spec.data || {}
    spec.data.values = data
  }
  const extras = {}
  const docLang = document.documentElement.lang
  if (docLang !== 'en' && LOCALE[docLang]) {
    spec.config = spec.config || {}
    if (!spec.config.locale) {
      spec.config.locale = LOCALE[docLang]
      extras.formatLocale = LOCALE[docLang].number
      extras.timeFormatLocale = LOCALE[docLang].time
    }
  }

  if (spec.columns) {
    // If we have a facet chart with columns and
    if (el.clientWidth < 500) {
      spec.columns = Math.floor(spec.columns / 2)
    }
  } else if (spec.width === undefined) {
    // Only set container width on non-facet charts
    spec.width = 'container'
    spec.autosize = 'fit'
  }
  const showActions = document.location.href.indexOf('admin') !== -1

  embed(el, spec, {
    ast: true,
    expr: expressionInterpreter,
    renderer: 'svg',
    actions: showActions,
    tooltip: bootstrapTooltipHandler,
    config: mergeConfig(colorTheme, spec.config),
    ...extras
  })
})
