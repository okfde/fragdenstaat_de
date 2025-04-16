<template>
  <div class="mb-4">
    <h3 class="mt-0 mb-2">
      <a :href="url" rel="noopener nofollow noreferrer" target="_blank">{{
        title
      }}</a>
    </h3>
    <div class="small mb-2">{{ site }}</div>
    <div class="tight-margin">
      <p class="search-highlight" v-html="text"></p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { Result } from './opensearch-wrapper.vue'

const { result } = defineProps<{ result: Result }>()
const { title, url, text, site } = result
</script>
