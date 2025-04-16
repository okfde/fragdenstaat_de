import { createAppWithProps } from 'froide/frontend/javascript/lib/vue-helper'
import OpensearchWrapper from './components/opensearch/opensearch-wrapper.vue'

document
  .querySelectorAll('opensearch')
  .forEach((element) =>
    createAppWithProps(element, OpensearchWrapper)!.mount(element)
  )
