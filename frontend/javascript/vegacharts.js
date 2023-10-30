import '../styles/vega.scss'

import { expressionInterpreter } from 'vega-interpreter'
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

document.querySelectorAll('[data-vegachart]').forEach((el) => {
  let spec
  if (el.dataset.vegachartdata) {
    spec = JSON.parse(el.dataset.vegachartdata)
  } else {
    spec = JSON.parse(document.getElementById(el.dataset.vegachart).textContent)
  }
  if (!spec.data.url && !spec.data.values && !spec.datasets) {
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

  // Slightly smaller than container
  if (spec.width === undefined) {
    spec.width = 'container'
    spec.autosize = 'fit'
  }
  const showActions = document.location.href.indexOf('admin') !== -1

  embed(el, spec, {
    ast: true,
    expr: expressionInterpreter,
    renderer: 'svg',
    actions: showActions,
    config: mergeConfig(colorTheme, spec.config),
    ...extras
  })
})
