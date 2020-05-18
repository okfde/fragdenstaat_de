import Vue from "vue"
import VuePivottable from 'vue-pivottable'

import App from './components/pivot/App.vue'

Vue.use(VuePivottable)

  
new Vue({
  render: h => h(App)
}).$mount("#pivot-app")
