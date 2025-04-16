<template>
  <form
    class="row mb-4"
    role="search"
    @submit.prevent="(event) => $emit('search', event.target!.search.value)"
  >
    <div class="col">
      <div class="input-group">
        <input
          class="form-control"
          type="text"
          name="search"
          :placeholder="props.i18n.search"
          :aria-label="props.i18n.search"
          :value="props.query"
        />
        <button class="btn btn-outline-primary" type="submit">
          <i class="fa fa-search" aria-hidden="true"></i>
          {{ props.i18n.search }}
        </button>
      </div>
    </div>
  </form>
</template>

<script lang="ts" setup>
const props = defineProps<{ i18n: Record<string, string>; query?: string }>()
defineEmits(['search'])
</script>
