<template>
  <nav class="mt-4">
    <ul class="pagination">
      <li class="page-item">
        <button
          aria-label="Previous"
          class="page-link"
          :class="{ disabled: !hasPrevious }"
          :disabled="!hasPrevious"
          @click="$emit('previous')"
        >
          <span aria-hidden="true">&laquo;</span>
        </button>
      </li>
      <li class="page-item disabled">
        <span v-if="props.maxPage !== 0" class="page-link">
          {{ props.currentPage + 1 }} / {{ props.maxPage }}
        </span>
        <span v-else class="page-link">
          {{ props.currentPage + 1 }}
        </span>
      </li>
      <li class="page-item">
        <button
          aria-label="Next"
          class="page-link"
          :class="{
            disabled: !hasNext
          }"
          :disabled="!hasNext"
          @click="$emit('next')"
        >
          <span aria-hidden="true">&raquo;</span>
        </button>
      </li>
    </ul>
  </nav>
</template>

<script lang="ts" setup>
const props = defineProps<{
  currentPage: number
  maxPage: number
}>()
defineEmits(['previous', 'next'])

const hasPrevious = props.currentPage !== 0
const hasNext = props.currentPage < props.maxPage
</script>
