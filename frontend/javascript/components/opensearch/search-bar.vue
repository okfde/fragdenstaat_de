<template>
  <form
    class="row mb-4"
    role="search"
    @submit.prevent="
      (event) =>
        $emit('search', event.target!.search.value, event.target!.site.value)
    "
  >
    <div class="d-grid gap-2 d-md-flex">
      <select
        class="form-select w-auto mw-md-25"
        name="site"
        :value="props.site"
      >
        <option
          v-for="(siteUrl, siteName) in filterConfig"
          :value="siteUrl"
          :key="siteUrl"
        >
          {{ siteName }}
        </option>
      </select>
      <input
        class="form-control"
        type="text"
        name="search"
        :placeholder="props.i18n.search"
        :aria-label="props.i18n.search"
        :value="props.query"
      />
      <button class="btn btn-outline-primary flex-shrink-0" type="submit">
        <i class="fa fa-search" aria-hidden="true"></i>
        {{ props.i18n.search }}
      </button>
    </div>
  </form>
</template>

<script lang="ts" setup>
const props = defineProps<{
  i18n: Record<string, string>
  query?: string
  site?: string
  filterConfig: Record<string, string>
}>()
defineEmits(['search'])
</script>
