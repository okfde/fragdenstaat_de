<!-- App.vue (template) -->
<template>
  <div>

    <vue-pivottable-ui
      :data="pivotData"
      :aggregatorName="aggregatorName"
      :rendererName="rendererName"
      :rows="rows"
      :cols="cols"
      :vals="vals"
      :derivedAttributes="derivedAttributes"
    >
    </vue-pivottable-ui>
 </div>
</template>

<script>
import 'vue-pivottable/dist/vue-pivottable.css'

import {derivers} from 'vue-pivottable/src/helper/utils.js'

const getWeek = function(date) {
    var onejan = new Date(date.getFullYear(), 0, 1);
    return Math.ceil((((date - onejan) / 86400000) + onejan.getDay() + 1) / 7);
}

export default {
  name: "app",
  components: {
    // VuePivottable -> is used via Vue.use in pivot.js
  },
  data () {
    let data = [[]]
    let config = {}
    try {
      data = JSON.parse(document.getElementById('pivot-data').textContent);
    } catch (err) {
      console.error(err)
    }
    try {
      config = JSON.parse(document.getElementById('pivot-config').textContent);
    } catch (err) {
      console.error(err)
    }

    let index = data[0]
    data = data.map((row, i) => {
      if (i === 0) return row
      return row.map((v, j) => {
        if (index[j].indexOf('time') === -1 && index[j].indexOf('date') === -1) {
          return v
        }
        return new Date(v)
      })
    })

    const yearDeriver = derivers.dateFormat(config.dateColumn, "%y")
    
    return {
      pivotData: data,
      aggregatorName: 'Sum',
      rendererName: 'Table Heatmap',

      derivedAttributes: {
        "year": yearDeriver,
        "year month": derivers.dateFormat(config.dateColumn, "%y-%m"),
        "month": derivers.dateFormat(config.dateColumn, "%m"),
        "day name": derivers.dateFormat(config.dateColumn, "%w"),
        "year week": (r) => `${yearDeriver(r)}-KW${getWeek(r[config.dateColumn])}`,
        "week": (r) => `KW${getWeek(r[config.dateColumn])}`
      },
      vals: [],
      rows: [],
      cols: [],
      ...config.extra
    }
  }
}
</script>
