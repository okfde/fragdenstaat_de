import { Tooltip, ScrollSpy } from 'bootstrap'
import '../styles/bookpub.scss'

function createFootnotePopover(content) {
  const footnotes = content.querySelectorAll('.footnote-ref')
  footnotes.forEach((footnote) => {
    new Tooltip(footnote, {
      //   container: footnote.parentElement.parentElement,
      html: true,
      placement: 'top',
      //   trigger: 'hover',
      title: () => {
        const id = footnote.getAttribute('href').replace('#', '')
        const note = document.getElementById(id)
        if (!note) {
          return ''
        }
        return note.innerHTML
      }
    })
  })
}

function generateSubToc(level, headings, start = 1) {
  const ul = document.createElement('ul')
  if (level === start) {
    ul.classList.add('list-unstyled')
  }
  let lastLi = null
  for (let i = 0; i < headings.length; i += 1) {
    const heading = headings[i]
    const headingLevel = parseInt(heading.tagName.substring(1), 10)
    if (headingLevel < level) {
      return ul
    }
    if (headingLevel > level) {
      const subToc = generateSubToc(level + 1, headings)
      i = i - 1
      if (lastLi !== null) {
        lastLi.appendChild(subToc)
      } else {
        lastLi = document.createElement('li')
        ul.appendChild(lastLi)
      }
      continue
    }
    headings.splice(0, 1)
    i = i - 1
    lastLi = document.createElement('li')
    lastLi.className = 'toc-li-' + heading.tagName.toLowerCase()
    const a = document.createElement('a')
    a.href = '#' + heading.id
    a.className = 'toc-link-' + heading.tagName.toLowerCase()
    a.textContent = heading.textContent
    lastLi.appendChild(a)
    ul.appendChild(lastLi)
  }
  return ul
}

function setupScrollSpy(content, toc) {
  new ScrollSpy(content, {
    target: toc
  })
}

function generateToc(content, toc) {
  const headings = content.querySelectorAll('h2, h3')
  const headingArray = Array.from(headings).filter(
    (heading) => heading.textContent !== ''
  )
  if (headingArray.length < 3) {
    return
  }
  const ul = generateSubToc(2, headingArray, 2)
  toc.appendChild(ul)
}

const content = document.getElementById('content')
const toc = document.getElementById('toc')

if (content != null) {
  createFootnotePopover(content)
  if (toc != null) {
    generateToc(content, toc)
    setupScrollSpy(content, toc)
  }
}
