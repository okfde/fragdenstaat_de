<template>
  <SearchBar @search="handleSearch" :i18n="i18n" :query="searchParams?.query" />
  <div class="d-flex flex-column align-items-center">
    <template v-if="searchParams">
      <template v-if="searchResults === null">
        <div class="spinner-border" role="status"></div>
      </template>
      <div v-else-if="searchResults.length > 0" class="w-100">
        <SearchResult
          v-for="result in searchResults"
          :key="result.id"
          :result="result"
        />
      </div>
      <div v-else>{{ i18n.noResults }}</div>
      <nav class="mt-4">
        <ul class="pagination">
          <li class="page-item">
            <button
              aria-label="Previous"
              class="page-link"
              :class="{ disabled: searchParams.currentPage === 0 }"
              :disabled="searchParams.currentPage === 0"
              @click="searchParams.currentPage--"
            >
              <span aria-hidden="true">&laquo;</span>
            </button>
          </li>
          <li class="page-item disabled">
            <span v-if="searchParams?.maxPage !== 0" class="page-link">
              {{ searchParams?.currentPage + 1 }} / {{ searchParams?.maxPage }}
            </span>
            <span v-else class="page-link">
              {{ searchParams?.currentPage + 1 }}
            </span>
          </li>
          <li class="page-item">
            <button
              aria-label="Next"
              class="page-link"
              :class="{
                disabled: searchParams.currentPage >= searchParams.maxPage
              }"
              :disabled="searchParams.currentPage >= searchParams.maxPage"
              @click="searchParams.currentPage++"
            >
              <span aria-hidden="true">&raquo;</span>
            </button>
          </li>
        </ul>
      </nav>
    </template>
  </div>
</template>

<script lang="ts" setup>
import SearchBar from './search-bar.vue'
import SearchResult from './search-result.vue'
import DOMPurify from 'dompurify'
import { ref, watch, onWatcherCleanup, Ref, onMounted } from 'vue'

const ITEMS_PER_PAGE = 10

export type Result = {
  title: string
  url: string
  id: string
  text: string
  site: string
}
type SearchParams = { query: string; currentPage: number; maxPage: number }

const props = defineProps<{
  endpoint: string
  urltemplate: string
  i18n: string
}>()
const i18n = JSON.parse(props.i18n)

const searchParams: Ref<SearchParams | null> = ref(null)
const searchResults: Ref<Result[] | null> = ref(null)

function handleSearch(search: string) {
  searchParams.value = { query: search, currentPage: 0, maxPage: 0 }
  window.history.pushState(null, '', '?q=' + encodeURIComponent(search))
}

function getElementContent(item: Element | Document, tagName: string): string {
  return item.getElementsByTagName(tagName)[0].textContent!
}

onMounted(() => {
  const urlParams = new URLSearchParams(window.location.search)
  if (urlParams.has('q')) {
    handleSearch(urlParams.get('q')!)
  }
})

watch(
  (): [string | undefined, number | undefined] => [
    searchParams.value?.query,
    searchParams.value?.currentPage
  ],
  ([query, page]: [string | undefined, number | undefined]) => {
    if (query !== undefined) {
      searchResults.value = null

      const controller = new AbortController()

      const searchUrl = new URL(props.endpoint)
      if (page) {
        searchUrl.searchParams.set('p', (page * ITEMS_PER_PAGE).toString())
      }
      searchUrl.searchParams.set('q', query)
      searchUrl.searchParams.set('n', ITEMS_PER_PAGE.toString())

      fetch(searchUrl, { signal: controller.signal })
        .then((response) => response.text())
        .then((text) => {
          const parser = new DOMParser()
          const doc = parser.parseFromString(text, 'text/xml')
          searchResults.value = Array.from(
            doc.getElementsByTagName('item')
          ).map((item) => {
            const date = getElementContent(item, 'date')
            const link = getElementContent(item, 'link')
            const collection = getElementContent(item, 'collection')
            const result = {
              title: getElementContent(item, 'title'),
              url: props.urltemplate
                .replace('$collection', collection)
                .replace('$link', link)
                .replace('$date', date),
              id: getElementContent(item, 'docId'),
              text: DOMPurify.sanitize(getElementContent(item, 'description')),
              site: getElementContent(item, 'site')
            }
            return result
          })
          searchParams.value!.maxPage = Math.ceil(
            parseInt(getElementContent(doc, 'totalResults')) /
              parseInt(getElementContent(doc, 'itemsPerPage'))
          )
        })

      onWatcherCleanup(() => {
        controller.abort()
      })
    }
  }
)
</script>
