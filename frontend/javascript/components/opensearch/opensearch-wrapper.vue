<template>
  <SearchBar
    @search="handleSearch"
    :i18n="i18n"
    :query="searchParams?.query"
    :filter-config="filterConfig"
    :site="searchParams?.site"
  />
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
      <SearchPagination
        :current-page="searchParams.currentPage"
        :max-page="searchParams.maxPage"
        @previous="searchParams.currentPage--"
        @next="searchParams.currentPage++"
      />
    </template>
  </div>
</template>

<script lang="ts" setup>
import SearchBar from './search-bar.vue'
import SearchPagination from './search-pagination.vue'
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

type SearchParams = {
  query: string
  currentPage: number
  maxPage: number
  site: string
}

const props = defineProps<{
  endpoint: string
  urltemplate: string
  i18n: string
  filterconfig: string
}>()

const i18n = JSON.parse(props.i18n)
const filterConfig = JSON.parse(props.filterconfig)

const searchParams: Ref<SearchParams | null> = ref(null)
const searchResults: Ref<Result[] | null> = ref(null)

function handleSearch(query: string, site: string) {
  searchParams.value = { query, site, currentPage: 0, maxPage: 0 }
  window.history.pushState(
    null,
    '',
    '?q=' + encodeURIComponent(query) + '&site=' + encodeURIComponent(site)
  )
}

function getElementContent(item: Element | Document, tagName: string): string {
  return item.getElementsByTagName(tagName)[0].textContent!
}

function parseSearchResult(text: string) {
  const parser = new DOMParser()
  const doc = parser.parseFromString(text, 'text/xml')
  searchResults.value = Array.from(doc.getElementsByTagName('item')).map(
    (item) => {
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
    }
  )
  searchParams.value!.maxPage = Math.ceil(
    parseInt(getElementContent(doc, 'totalResults')) /
      parseInt(getElementContent(doc, 'itemsPerPage'))
  )
}

function getSearchUrl(query: string, page: number, site: string) {
  const searchUrl = new URL(props.endpoint)
  if (page) {
    searchUrl.searchParams.set('p', (page * ITEMS_PER_PAGE).toString())
  }
  searchUrl.searchParams.set('q', query)
  searchUrl.searchParams.set('n', ITEMS_PER_PAGE.toString())
  searchUrl.searchParams.append('s', site)
  return searchUrl
}

onMounted(() => {
  const urlParams = new URLSearchParams(window.location.search)
  if (urlParams.has('q') && urlParams.has('site')) {
    handleSearch(urlParams.get('q')!, urlParams.get('site')!)
  }
})

watch(
  (): [string | undefined, number | undefined, string | undefined] => [
    searchParams.value?.query,
    searchParams.value?.currentPage,
    searchParams.value?.site
  ],
  ([query, page, site]: [
    string | undefined,
    number | undefined,
    string | undefined
  ]) => {
    if (query !== undefined && page !== undefined && site !== undefined) {
      searchResults.value = null

      const controller = new AbortController()
      const searchUrl = getSearchUrl(query, page, site)

      fetch(searchUrl, { signal: controller.signal })
        .then((response) => response.text())
        .then(parseSearchResult)

      onWatcherCleanup(() => {
        controller.abort()
      })
    }
  }
)
</script>
